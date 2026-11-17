#!/usr/bin/env python3
"""Collect GitHub repositories relevant to the lab, reproducibly.

- Runs every query in scope.json -> repoSearch.queries against the GitHub Search API.
- Merges results into data/repos.json without losing history (stable ids, firstSeen).
- Writes a query log (CSV) so every run can be reproduced and reported (e.g. in a review paper).
- Writes a dated changelog of new / changed / disappeared repos.

Standard library only. Set GITHUB_TOKEN for higher rate limits (Actions provides one).
Usage: python scripts/collect_repos.py [--dry-run] [--max-queries N] [--no-readme]
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCOPE = ROOT / "scope.json"
REPOS = ROOT / "data" / "repos.json"
LOGDIR = ROOT / "data" / "logs"
API = "https://api.github.com"
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>)\]]+)", re.I)
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.I)
PAPER_RE = re.compile(r"\b(paper|journal|published|preprint|thesis|dissertation|proceedings|doi|arxiv|ieee|elsevier|springer|wiley|mdpi|acs|rsc|nature|frontiers|plos)\b", re.I)
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense", "CC0-1.0", "0BSD", "BSL-1.0", "Zlib", "CC-BY-4.0"}
COPYLEFT = {"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0", "MPL-2.0", "EPL-2.0", "EUPL-1.2", "CC-BY-SA-4.0"}
USER_FIELDS = ("notes", "tierOverride", "exclude")  # never overwritten by the collector


def derive(rec):
    """Purpose flags used by the page's two views: 'reuse in lab' and 'cite in review'."""
    lic = rec.get("license")
    rec["licenseClass"] = "permissive" if lic in PERMISSIVE else "copyleft" if lic in COPYLEFT else "none" if lic is None else "other"
    rec["reusable"] = rec["licenseClass"] in ("permissive", "copyleft") and not rec.get("archived")
    ev = []
    if rec.get("citationFile"):
        ev.append("CITATION.cff")
    if rec.get("linkedDOIs"):
        ev.append("DOI in README")
    if rec.get("linkedArxiv"):
        ev.append("arXiv in README")
    if PAPER_RE.search(rec.get("description") or ""):
        ev.append("description mentions a publication")
    rec["paperEvidence"] = ev
    rec["hasPaper"] = bool(ev)
    return rec


def fetch_raw(full_name, path):
    try:
        url = f"https://raw.githubusercontent.com/{full_name}/HEAD/{path}"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lab-radar-collector"}), timeout=20) as r:
            return r.read(200_000).decode("utf-8", "replace")
    except Exception:
        return None


def today():
    return dt.date.today().isoformat()


def gh_get(path, params=None, accept="application/vnd.github+json", raw=False):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    headers = {"Accept": accept, "User-Agent": "lab-radar-collector", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(4):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read()
                return body.decode("utf-8", "replace") if raw else json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            limited = e.code == 429 or e.headers.get("X-RateLimit-Remaining") == "0" or e.headers.get("Retry-After")
            if e.code == 403 and not limited:
                raise  # genuinely forbidden, not a rate limit
            if limited:
                reset = e.headers.get("X-RateLimit-Reset")
                wait = max(5, int(reset) - int(time.time()) + 2) if reset else 30 * (attempt + 1)
                wait = min(wait, 120)
                print(f"  rate limited ({e.code}); waiting {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if 500 <= e.code < 600:
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError as e:
            print(f"  network error: {e}; retry", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"GitHub request failed after retries: {url}")


def fetch_readme(full_name):
    """README text via raw.githubusercontent.com (no API quota); API as fallback; never raises."""
    for name in ("README.md", "readme.md", "README.rst", "README.txt", "README"):
        url = f"https://raw.githubusercontent.com/{full_name}/HEAD/{name}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lab-radar-collector"}), timeout=20) as r:
                return r.read(400_000).decode("utf-8", "replace")
        except Exception:
            continue
    try:
        return gh_get(f"/repos/{full_name}/readme", accept="application/vnd.github.raw+json", raw=True)
    except Exception as e:
        print(f"  README unavailable for {full_name}: {e}", file=sys.stderr)
        return None


def text_of(item):
    name = (item.get("full_name") or "").replace("_", " ").replace("-", " ")
    return " ".join([name, item.get("description") or "", " ".join(t.replace("-", " ") for t in (item.get("topics") or []))]).lower()


def maintenance(item, active_months):
    if item.get("archived"):
        return "archived"
    pushed = item.get("pushed_at")
    if not pushed:
        return "stale"
    pushed_d = dt.date.fromisoformat(pushed[:10])
    return "active" if (dt.date.today() - pushed_d).days <= active_months * 30.44 else "stale"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="do not write files")
    ap.add_argument("--max-queries", type=int, default=0, help="run only the first N queries (testing)")
    ap.add_argument("--no-readme", action="store_true", help="skip README DOI extraction")
    args = ap.parse_args()

    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    cfg = scope["repoSearch"]
    queries = cfg["queries"][: args.max_queries] if args.max_queries else cfg["queries"]
    authed = bool(os.environ.get("GITHUB_TOKEN"))
    pause = 2.2 if authed else 6.5  # search API: 30/min authed, 10/min anonymous

    existing = {r["id"]: r for r in json.loads(REPOS.read_text(encoding="utf-8"))} if REPOS.exists() else {}
    seen_now = {}
    qlog = []
    run_date = today()

    for qi, q in enumerate(queries):
        fetched = kept = 0
        total = None
        terms = [re.compile(r"\b" + t, re.I) for t in q.get("mustMatchAny", [])]
        for page in range(1, cfg.get("pagesPerQuery", 1) + 1):
            full_q = f"{q['q']} fork:false"
            if cfg.get("minStars"):
                full_q += f" stars:>={cfg['minStars']}"
            res = gh_get("/search/repositories", {"q": full_q, "per_page": cfg.get("perPage", 100), "page": page})
            time.sleep(pause)
            if not res:
                break
            total = res.get("total_count", total)
            items = res.get("items", [])
            fetched += len(items)
            for it in items:
                rid = f"gh:{it['full_name']}"
                rec = seen_now.get(rid)
                matched_meta = any(t.search(text_of(it)) for t in terms) if terms else True
                if rec is None:
                    rec = {
                        "id": rid,
                        "fullName": it["full_name"],
                        "url": it["html_url"],
                        "description": it.get("description"),
                        "topics": it.get("topics") or [],
                        "language": it.get("language"),
                        "license": (it.get("license") or {}).get("spdx_id"),
                        "stars": it.get("stargazers_count", 0),
                        "forks": it.get("forks_count", 0),
                        "createdAt": (it.get("created_at") or "")[:10] or None,
                        "pushedAt": (it.get("pushed_at") or "")[:10] or None,
                        "archived": bool(it.get("archived")),
                        "maintenance": maintenance(it, cfg.get("activeMonths", 12)),
                        "subjects": [],
                        "tier": q["tier"],
                        "matchedQueries": [],
                        "needsReview": True,
                    }
                    seen_now[rid] = rec
                rec["tier"] = min(rec["tier"], q["tier"])
                rec["subjects"] = sorted(set(rec["subjects"]) | set(q.get("subjects", [])))
                if q["q"] not in rec["matchedQueries"]:
                    rec["matchedQueries"].append(q["q"])
                if matched_meta:
                    rec["needsReview"] = False
                kept += 1
            if len(items) < cfg.get("perPage", 100):
                break
        qlog.append({"date": run_date, "query": q["q"], "tier": q["tier"], "total_count": total, "fetched": fetched, "authenticated": authed})
        print(f"[{qi + 1}/{len(queries)}] {q['q']!r}: total={total} fetched={fetched}")

    # README DOI extraction for repos never checked before (bounded per run)
    if not args.no_readme:
        budget = cfg.get("readmeDoiCheckLimit", 100)
        for rid, rec in seen_now.items():
            old = existing.get(rid, {})
            if old.get("readmeChecked"):
                for f in ("linkedDOIs", "linkedArxiv", "citationFile", "readmeChecked"):
                    if f in old:
                        rec[f] = old[f]
                continue
            if budget <= 0:
                break
            budget -= 1
            txt = fetch_readme(rec["fullName"])
            if txt is None:
                continue  # fetch failed: leave unchecked so the next run retries
            rec["linkedDOIs"] = sorted({d.rstrip(".,;") for d in DOI_RE.findall(txt)})[:10]
            rec["linkedArxiv"] = sorted(set(ARXIV_RE.findall(txt)))[:10]
            rec["citationFile"] = fetch_raw(rec["fullName"], "CITATION.cff") is not None
            rec["readmeChecked"] = run_date
            time.sleep(0.3 if authed else 1.0)

    # Merge with history
    merged, changes = {}, {"new": [], "changed": [], "missing": []}
    for rid, rec in seen_now.items():
        old = existing.get(rid)
        rec["firstSeen"] = old.get("firstSeen", run_date) if old else run_date
        rec["lastSeen"] = run_date
        rec["sourceDate"] = run_date
        for f, default in (("linkedDOIs", []), ("linkedArxiv", []), ("citationFile", False)):
            rec.setdefault(f, old.get(f, default) if old else default)
        if old:
            for f in USER_FIELDS:
                if f in old:
                    rec[f] = old[f]
            diffs = [f for f in ("stars", "pushedAt", "archived", "tier", "description") if old.get(f) != rec.get(f)]
            if diffs:
                changes["changed"].append(f"{rid}: " + ", ".join(f"{f} {old.get(f)!r}→{rec.get(f)!r}" for f in diffs))
        else:
            changes["new"].append(f"{rid} (tier {rec['tier']}, ★{rec['stars']}{', needsReview' if rec['needsReview'] else ''})")
        merged[rid] = rec
    for rid, old in existing.items():
        if rid not in merged:
            merged[rid] = old  # keep history; it simply was not returned this run
            changes["missing"].append(f"{rid} (lastSeen {old.get('lastSeen')})")

    for rec in merged.values():
        derive(rec)
    out = sorted(merged.values(), key=lambda r: (r.get("tierOverride") or r["tier"], -r.get("stars", 0), r["id"]))
    print(f"repos: {len(out)} total | new {len(changes['new'])} | changed {len(changes['changed'])} | not returned {len(changes['missing'])}")

    if args.dry_run:
        return
    REPOS.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    LOGDIR.mkdir(parents=True, exist_ok=True)
    qfile = LOGDIR / "repo_queries.csv"
    new_file = not qfile.exists() or qfile.stat().st_size == 0
    with qfile.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(qlog[0].keys()) if qlog else ["date"])
        if new_file:
            w.writeheader()
        w.writerows(qlog)
    lines = [f"# Repo changelog {run_date}", ""]
    for k, title in (("new", "New"), ("changed", "Changed"), ("missing", "Not returned this run (kept)")):
        lines.append(f"## {title} ({len(changes[k])})")
        lines += [f"- {x}" for x in changes[k][:500]] or ["- none"]
        lines.append("")
    (LOGDIR / f"repos-{run_date}.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
