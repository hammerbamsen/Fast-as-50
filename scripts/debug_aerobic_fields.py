"""Diagnose runde 2: raadata til design af EF-filteret.

Runde 1 viste: icu_efficiency_factor og decoupling findes, men er KUN udfyldt
naar der er power (33/183 pas). Loeb faar None. Loebe-EF skal derfor beregnes
selv — og spoergsmaalet er om `gap` (grade adjusted pace) er udfyldt, saa
bakker kan korrigeres i stedet for at kaste passet vaek.
"""
import sys, os
from datetime import date, timedelta
sys.path.insert(0, os.path.dirname(__file__))
from modules.config import BASE, AUTH, api_get


def main():
    newest = date.today()
    oldest = newest - timedelta(days=120)
    r = api_get(f'{BASE}/activities', auth=AUTH,
                params={'oldest': str(oldest), 'newest': str(newest), 'limit': 400})
    if not r or r.status_code != 200:
        print(f"FEJL HTTP {getattr(r,'status_code','n/a')}"); return 1
    acts = r.json() or []

    runs  = [a for a in acts if a.get('type') in ('Run', 'TrailRun', 'VirtualRun')]
    rides = [a for a in acts if a.get('type') in ('Ride', 'VirtualRide', 'GravelRide')]

    for f in ('gap', 'pace', 'average_speed', 'average_heartrate', 'total_elevation_gain',
              'threshold_pace', 'icu_intensity', 'trainer', 'race', 'commute'):
        n = sum(1 for a in runs if a.get(f) not in (None, '', []))
        print(f"LOEB-daekning {f:24s} {n:3d}/{len(runs)}")

    print(f"\n=== ALLE LOEB ({len(runs)}) — dato|min|km|hm|hm/km|avgspd|gap|HR|IF|navn")
    for a in sorted(runs, key=lambda x: x.get('start_date_local') or ''):
        mt = (a.get('moving_time') or 0) / 60
        km = (a.get('distance') or 0) / 1000
        hm = a.get('total_elevation_gain') or 0
        hpk = hm / km if km else 0
        print(f"  {(a.get('start_date_local') or '')[:10]} {mt:6.0f} {km:6.2f} {hm:6.0f} "
              f"{hpk:6.1f} {str(a.get('average_speed')):>7s} {str(a.get('gap')):>7s} "
              f"{str(a.get('average_heartrate')):>5s} {str(round(a.get('icu_intensity') or 0)):>4s} "
              f"| {(a.get('name') or '')[:38]}")

    print(f"\n=== ALLE CYKELPAS ({len(rides)}) — dato|min|IF|EF|dec|trainer|NP|HR|navn")
    for a in sorted(rides, key=lambda x: x.get('start_date_local') or ''):
        mt = (a.get('moving_time') or 0) / 60
        print(f"  {(a.get('start_date_local') or '')[:10]} {mt:6.0f} "
              f"{str(round(a.get('icu_intensity') or 0)):>4s} "
              f"{str(a.get('icu_efficiency_factor')):>10s} "
              f"{str(round(a['decoupling'],1) if a.get('decoupling') is not None else None):>7s} "
              f"{str(a.get('trainer')):>5s} {str(a.get('icu_weighted_avg_watts')):>5s} "
              f"{str(a.get('average_heartrate')):>5s} | {(a.get('name') or '')[:34]}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
