#!/usr/bin/env python3
"""Skub zoner fra data/plan.json til Intervals.icu sport-settings.

plan.json er master. Dette script skriver ALDRIG til plan.json.

Cykel: zones.ftpW          -> felt "ftp"            (heltal watt)
Loeb:  zones.thresholdSec  -> felt "threshold_pace" (ENHED m/s = 1000/sek_per_km)

Env:
  INTERVALS_API_KEY  (paakraevet)
  SPORT              bike | run | both   (default: bike)
  DRY_RUN            true | false        (default: true)
"""
import json
import os
import sys

import requests

ATHLETE = "i599466"
BASE = f"https://intervals.icu/api/v1/athlete/{ATHLETE}/sport-settings"
SPORT_IDS = {"bike": 2484017, "run": 2484018}
PLAN = "data/plan.json"


def target_value(sport, zones):
    """Returner (feltnavn, vaerdi) udledt af plan.json."""
    if sport == "bike":
        return "ftp", int(zones["ftpW"])
    # 4:20/km = 260 sek/km -> 1000/260 = 3.8461538 m/s
    return "threshold_pace", 1000.0 / float(zones["thresholdSec"])


def same(field, a, b):
    if a is None:
        return False
    if field == "ftp":
        return int(a) == int(b)
    return abs(float(a) - float(b)) < 1e-4


def main():
    key = os.environ.get("INTERVALS_API_KEY", "").strip()
    if not key:
        sys.exit("FEJL: INTERVALS_API_KEY er tom")

    sport_arg = os.environ.get("SPORT", "bike").strip().lower()
    dry = os.environ.get("DRY_RUN", "true").strip().lower() != "false"
    sports = ["bike", "run"] if sport_arg == "both" else [sport_arg]
    for s in sports:
        if s not in SPORT_IDS:
            sys.exit(f"FEJL: ukendt sport '{s}' (brug bike, run eller both)")

    with open(PLAN, encoding="utf-8") as fh:
        zones = json.load(fh)["athletes"]["kennet"]["zones"]

    auth = ("API_KEY", key)
    r = requests.get(BASE, auth=auth, timeout=30)
    r.raise_for_status()
    allset = {s["id"]: s for s in r.json()}

    print(f"MODE: {'DRY-RUN (ingen skrivning)' if dry else 'LIVE'}  SPORT: {sports}")
    failures = []

    for sport in sports:
        sid = SPORT_IDS[sport]
        cur = allset.get(sid)
        if cur is None:
            failures.append(f"{sport}: sport-id {sid} findes ikke")
            continue

        field, want = target_value(sport, zones)
        have = cur.get(field)
        print(f"\n--- {sport.upper()} (id {sid}, types={cur.get('types')}) ---")
        print(f"  {field}: {have}  ->  {want}")

        if same(field, have, want):
            print("  uaendret, springer over")
            continue
        if dry:
            print("  DRY-RUN: ingen PUT sendt")
            continue

        body = dict(cur)
        body[field] = want
        resp = requests.put(f"{BASE}/{sid}", auth=auth, json=body, timeout=30)
        path = f"{BASE}/{sid}"
        if resp.status_code in (400, 404, 405):
            print(f"  PUT /{sid} gav {resp.status_code} - proever collection-PUT")
            resp = requests.put(BASE, auth=auth, json=[body], timeout=30)
            path = BASE
        print(f"  PUT {path} -> HTTP {resp.status_code}")
        if resp.status_code >= 300:
            failures.append(f"{sport}: PUT {resp.status_code} {resp.text[:200]}")
            continue

        # Verificer INDHOLD, ikke status
        v = requests.get(BASE, auth=auth, timeout=30)
        v.raise_for_status()
        after = {s["id"]: s for s in v.json()}.get(sid, {}).get(field)
        print(f"  VERIFIKATION re-GET: {field} = {after}")
        if not same(field, after, want):
            failures.append(f"{sport}: re-GET viser {after}, forventede {want}")
        else:
            print("  OK")

    if failures:
        print("\nFEJL:")
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("\nFaerdig uden fejl.")


if __name__ == "__main__":
    main()
