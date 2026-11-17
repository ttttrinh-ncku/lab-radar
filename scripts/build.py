#!/usr/bin/env python3
"""Build self-contained HTML pages from template/index.template.html + data/*.json.

Outputs
  site/index.html          public page (events + repos; jobs EXCLUDED) -> GitHub Pages
  site/data.json           same public data as machine-readable JSON
  private/report_full.html everything incl. data/jobs.json (git-ignored; open by double-click)

Usage: python scripts/build.py
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template" / "index.template.html"


def load(name):
    p = ROOT / "data" / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def render(payload):
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")  # safe inside <script>
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", blob)


def main():
    scope = json.loads((ROOT / "scope.json").read_text(encoding="utf-8"))
    meta = {
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "subjects": scope["subjects"],
        "regions": scope["regions"],
        "tiers": scope["tiers"],
        "deadlineAlertDays": scope.get("deadlineAlertDays", 30),
        "owner": scope.get("owner", ""),
        "siteTitle": scope.get("siteTitle"),
    }
    events = [e for e in load("events.json")]
    repos = [r for r in load("repos.json") if not r.get("exclude")]
    jobs = load("jobs.json")

    public = {"meta": {**meta, "includesJobs": False}, "events": events, "repos": repos, "jobs": []}
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(render(public), encoding="utf-8")
    (site / "data.json").write_text(json.dumps(public, ensure_ascii=False, indent=1), encoding="utf-8")
    (site / ".nojekyll").write_text("", encoding="utf-8")

    priv = ROOT / "private"
    priv.mkdir(exist_ok=True)
    full = {"meta": {**meta, "includesJobs": True}, "events": events, "repos": repos, "jobs": jobs}
    (priv / "report_full.html").write_text(render(full), encoding="utf-8")
    print(f"built site/index.html ({len(events)} events, {len(repos)} repos) and private/report_full.html (+{len(jobs)} jobs)")


if __name__ == "__main__":
    main()
