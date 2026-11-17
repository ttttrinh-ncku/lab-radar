#!/usr/bin/env python3
"""Validate Lab Radar data against schema/DATA_FORMAT.md and report recall against data/gold_list.json.

Exit code 1 if any ERROR (bad enums, fake nulls, malformed dates, duplicate ids...).
WARN items need human attention (stale sources, past events not archived, deadlines soon).
Usage: python scripts/validate.py [--quiet]
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
scope = json.loads((ROOT / "scope.json").read_text(encoding="utf-8"))
TODAY = dt.date.today()
ALERT = scope.get("deadlineAlertDays", 30)
STALE = scope.get("staleSourceDays", 30)

SUBJECTS = set(scope["subjects"])
REGIONS = set(scope["regions"])
NORDIC = set(scope["nordicCountries"])
EV_KIND = {"Conference", "Workshop", "Summer School", "Special Issue"}
EV_MODE = {"In-person", "Hybrid", "Online", "Journal"}
EV_STATUS = {"Announced", "Open", "Closed", "Watchlist", "Archived", "Cancelled"}
MILESTONES = {"abstract", "full_paper", "special_session", "notification", "camera_ready", "early_bird", "registration"}
SUBMISSION = {"abstract", "full_paper", "special_session"}
JOB_ROLE = set(scope["jobRoles"])
JOB_MODE = {"Onsite", "Hybrid", "Remote"}
JOB_STATUS = {"Active", "Closed", "Unverified", "Archived"}
VERIF = {"full", "partial", "lead"}
FAKE_NULL = {"n/a", "na", "tba", "tbd", "null", "none", "unknown", "-", ""}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CC = re.compile(r"^[A-Z]{2}$")
CUR = re.compile(r"^[A-Z]{3}$")

errors, warns, infos = [], [], []


def E(rid, msg): errors.append(f"ERROR {rid}: {msg}")
def W(rid, msg): warns.append(f"WARN  {rid}: {msg}")
def I(rid, msg): infos.append(f"INFO  {rid}: {msg}")


def date_ok(rid, field, v, allow_null=True):
    if v is None:
        if not allow_null:
            E(rid, f"{field} is required")
        return None
    if not isinstance(v, str) or not ISO.match(v):
        E(rid, f"{field}={v!r} must be YYYY-MM-DD or null (never 'TBA'/'N/A')")
        return None
    try:
        return dt.date.fromisoformat(v)
    except ValueError:
        E(rid, f"{field}={v!r} is not a real date")
        return None


def common(r, kind):
    rid = r.get("id") or "<no id>"
    if not r.get("id"):
        E(rid, "missing id")
    if not r.get("title"):
        E(rid, "missing title")
    for f, v in r.items():
        if isinstance(v, str) and v.strip().lower() in FAKE_NULL and f not in ("notes", "requirements", "description"):
            E(rid, f"{f}={v!r} is a fake null; use null")
    subs = r.get("subjects") or []
    if not subs or not set(subs) <= SUBJECTS:
        E(rid, f"subjects {subs} must be a non-empty subset of {sorted(SUBJECTS)}")
    if r.get("tier") not in (1, 2, 3):
        E(rid, f"tier={r.get('tier')!r} must be 1, 2 or 3")
    if r.get("region") not in REGIONS:
        E(rid, f"region={r.get('region')!r} not in {sorted(REGIONS)}")
    c = r.get("country")
    if c is not None and not CC.match(str(c)):
        E(rid, f"country={c!r} must be ISO alpha-2 or null")
    if c in NORDIC and r.get("region") != "NORDIC":
        E(rid, f"country {c} is Nordic but region={r.get('region')}")
    if r.get("verification") not in VERIF:
        E(rid, f"verification={r.get('verification')!r} not in {sorted(VERIF)}")
    sd = date_ok(rid, "sourceDate", r.get("sourceDate"), allow_null=False)
    if sd and (TODAY - sd).days > STALE and r.get("status") not in ("Archived", "Cancelled", "Closed"):
        W(rid, f"source last checked {sd} (> {STALE} days) — re-verify")
    if not r.get("urls") and r.get("status") != "Watchlist":
        E(rid, "no official url")
    for cf in r.get("conflicts", []) or []:
        if not {"field", "values", "resolution"} <= set(cf):
            E(rid, "conflicts entries need field, values, resolution")
    return rid


def check_events(evs):
    for r in evs:
        rid = common(r, "event")
        if r.get("kind") not in EV_KIND:
            E(rid, f"kind={r.get('kind')!r} not in {sorted(EV_KIND)}")
        if r.get("mode") not in EV_MODE:
            E(rid, f"mode={r.get('mode')!r} not in {sorted(EV_MODE)}")
        st = r.get("status")
        if st not in EV_STATUS:
            E(rid, f"status={st!r} not in {sorted(EV_STATUS)}")
        s = date_ok(rid, "startDate", r.get("startDate"))
        e = date_ok(rid, "endDate", r.get("endDate"))
        if s and e and e < s:
            E(rid, "endDate before startDate")
        if st == "Watchlist" and s:
            E(rid, "Watchlist items must not carry a startDate (no inferred dates)")
        last = e or s
        if last and last < TODAY and st not in ("Archived", "Cancelled"):
            W(rid, f"event ended {last} — set status Archived")
        if s and (s - TODAY).days > scope.get("rollingWindowMonths", 18) * 31:
            W(rid, f"starts {s}, beyond the rolling window")
        open_sub = False
        for m in r.get("milestones", []) or []:
            if m.get("type") not in MILESTONES:
                E(rid, f"milestone type {m.get('type')!r} invalid")
            d = date_ok(rid, f"milestone[{m.get('type')}]", m.get("date"))
            if d:
                left = (d - TODAY).days
                if m.get("type") in SUBMISSION and left >= 0:
                    open_sub = True
                if 0 <= left <= ALERT:
                    I(rid, f"{m['type']} deadline {d} in {left} days ({m.get('tz') or 'tz not stated'})")
                if m.get("tz") is None:
                    W(rid, f"milestone {m['type']} {d} has no time zone")
        if st == "Open" and not open_sub and not any((m.get("date") is None) for m in r.get("milestones", [])):
            W(rid, "status Open but no future submission milestone")
        fee = r.get("fee") or {}
        if fee.get("value") is not None:
            if not fee.get("currency") or not CUR.match(fee["currency"]) or not fee.get("basis"):
                E(rid, "fee.value requires ISO currency and basis")
            if fee.get("value") == 0 and "free" not in (fee.get("text") or "").lower():
                E(rid, "fee.value 0 requires explicit 'free' confirmation in fee.text")
        if r.get("remotePresentation") not in ("yes", "no", None):
            E(rid, "remotePresentation must be 'yes', 'no' or null")


def check_jobs(jobs):
    for r in jobs:
        rid = common(r, "job")
        if r.get("roleType") not in JOB_ROLE:
            E(rid, f"roleType={r.get('roleType')!r} not in {sorted(JOB_ROLE)}")
        if r.get("mode") not in JOB_MODE:
            E(rid, f"mode={r.get('mode')!r} not in {sorted(JOB_MODE)}")
        st = r.get("status")
        if st not in JOB_STATUS:
            E(rid, f"status={st!r} not in {sorted(JOB_STATUS)}")
        d = date_ok(rid, "deadline", r.get("deadline"))
        if d:
            left = (d - TODAY).days
            if left < 0 and st == "Active":
                W(rid, f"deadline {d} passed but status Active")
            elif 0 <= left <= ALERT and st == "Active":
                I(rid, f"application deadline {d} in {left} days")
            if r.get("tz") is None:
                W(rid, "deadline without time zone")
        sal = r.get("salary") or {}
        if sal.get("value") is not None and not (sal.get("currency") and sal.get("period") and sal.get("basis")):
            E(rid, "salary.value requires currency, period and basis")


def check_repos(repos):
    for r in repos:
        rid = r.get("id", "<no id>")
        if not str(rid).startswith("gh:"):
            E(rid, "repo id must be gh:<owner>/<name>")
        if r.get("tier") not in (1, 2, 3):
            E(rid, "bad tier")
        if r.get("maintenance") not in ("active", "stale", "archived"):
            E(rid, "bad maintenance")


def dupes(name, rows):
    ids = [r.get("id") for r in rows]
    for x in {i for i in ids if ids.count(i) > 1}:
        E(x, f"duplicate id in {name}")


def load(name):
    p = DATA / name
    if not p.exists():
        return []
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        E(name, f"invalid JSON: {e}")
        return []
    if not isinstance(v, list):
        E(name, "top level must be an array")
        return []
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="print only errors and the summary")
    args = ap.parse_args()
    evs, jobs, repos = load("events.json"), load("jobs.json"), load("repos.json")
    for n, rows in (("events", evs), ("jobs", jobs), ("repos", repos)):
        dupes(n, rows)
    check_events(evs)
    check_jobs(jobs)
    check_repos(repos)

    gold_p = DATA / "gold_list.json"
    recall = []
    if gold_p.exists():
        gold = json.loads(gold_p.read_text(encoding="utf-8"))
        for n, rows in (("events", evs), ("repos", repos), ("jobs", jobs)):
            want = gold.get(n) or []
            if want:
                have = {r.get("id") for r in rows}
                hit = [g for g in want if g in have]
                recall.append(f"recall {n}: {len(hit)}/{len(want)}" + (f" — missing: {', '.join(g for g in want if g not in have)}" if len(hit) < len(want) else ""))

    for line in errors:
        print(line)
    if not args.quiet:
        for line in warns + infos:
            print(line)
    for line in recall:
        print(line)
    print(f"summary: {len(evs)} events, {len(repos)} repos, {len(jobs)} jobs | {len(errors)} errors, {len(warns)} warnings, {len(infos)} alerts")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
