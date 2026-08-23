"""Diagnose: hvilke aerobe felter bærer Intervals.icu rent faktisk på en aktivitet?

Køres FØR aerobic.py kodes. Baggrund: `bodyFat` vs `Kropsfedt`-fælden 2026 —
UI-navnet er ikke API-navnet, og et gæt koster en hel debugging-runde.

Printer:
  1. Alle keys på en tilfældig cykel- og løbeaktivitet
  2. Kandidatfelter til EF og decoupling med faktiske værdier
  3. Dækningsgrad: hvor mange af de sidste 120 dages pas har felterne udfyldt
"""
import sys, os, json
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from modules.config import BASE, AUTH, api_get

CANDIDATES = [
    'icu_efficiency_factor', 'efficiency_factor', 'ef',
    'decoupling', 'icu_decoupling', 'icu_power_hr', 'power_hr',
    'icu_weighted_avg_watts', 'icu_average_watts', 'average_watts',
    'average_heartrate', 'icu_average_hr', 'average_speed',
    'icu_intensity', 'icu_ftp', 'moving_time', 'distance',
    'total_elevation_gain', 'trainer', 'icu_hr_zone_times',
]


def main():
    newest = date.today()
    oldest = newest - timedelta(days=120)
    r = api_get(f'{BASE}/activities', auth=AUTH,
                params={'oldest': str(oldest), 'newest': str(newest), 'limit': 400})
    if not r or r.status_code != 200:
        print(f"FEJL: HTTP {getattr(r, 'status_code', 'n/a')}")
        return 1

    acts = r.json() or []
    print(f"=== {len(acts)} aktiviteter i vinduet {oldest} -> {newest}")

    types = {}
    for a in acts:
        types[a.get('type')] = types.get(a.get('type'), 0) + 1
    print(f"=== Typer: {types}")

    # 1. Alle keys på ét eksempel per disciplin
    for want, label in ((('Ride', 'VirtualRide'), 'CYKEL'), (('Run',), 'LOEB')):
        ex = next((a for a in acts if a.get('type') in want), None)
        if not ex:
            print(f"\n=== {label}: ingen aktivitet fundet")
            continue
        print(f"\n=== {label} eksempel: id={ex.get('id')} "
              f"dato={(ex.get('start_date_local') or '')[:10]} type={ex.get('type')}")
        print(f"--- ALLE KEYS ({len(ex.keys())}):")
        print(sorted(ex.keys()))
        print(f"--- KANDIDATVAERDIER:")
        for c in CANDIDATES:
            if c in ex:
                v = ex[c]
                v = str(v)[:80] if isinstance(v, (list, dict)) else v
                print(f"    {c:28s} = {v}")
            else:
                print(f"    {c:28s} = <FELT FINDES IKKE>")

    # 2. Dækningsgrad over hele vinduet
    print(f"\n=== DAEKNINGSGRAD (ikke-null ud af {len(acts)} pas):")
    for c in CANDIDATES:
        n = sum(1 for a in acts if a.get(c) not in (None, 0, [], ''))
        print(f"    {c:28s} {n:4d}/{len(acts)}")

    # 3. Hvor mange lange Z2-pas findes overhovedet (grundlag for EF-signalet)
    long_easy = [a for a in acts
                 if (a.get('moving_time') or 0) >= 45 * 60
                 and (a.get('icu_intensity') or 0) and a['icu_intensity'] < 80
                 and a.get('type') in ('Ride', 'VirtualRide', 'Run')]
    print(f"\n=== Pas >=45 min med IF<0,80: {len(long_easy)}")
    for a in long_easy[:15]:
        print(f"    {(a.get('start_date_local') or '')[:10]} {a.get('type'):12s} "
              f"{round((a.get('moving_time') or 0)/60)} min  IF={a.get('icu_intensity')}  "
              f"EF={a.get('icu_efficiency_factor')}  dec={a.get('decoupling')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
