"""Engangsdiagnostik: hvilke cykelpas kunne lovligt tælle med i EF?

Kører READ-ONLY mod Intervals og skriver en tabel til debug/bike_ef_audit.txt.
Formålet er at sætte grænseværdier for udendørs EF på evidens i stedet for at
gætte. Ændrer ingen produktionsdata.

Nøgletal pr. pas:
  VI       = NP / gns. watt. Fladt, jævnt pas ~1,00-1,05. Bjergtur med
             nedkørsler ligger højt, fordi NP straffer variationen.
  hm/km    = stigning pr. km. Coasting følger nedkørsler, som følger stigning.
  coast    = andel af tiden uden pedaltryk, hvis feltet findes.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from modules.config import BASE, AUTH, api_get          # noqa: E402
from modules.aerobic import BIKE_TYPES, _hard_fraction, _is_aerobic  # noqa: E402

DAYS = 180
COAST_KEYS = ('coasting_time', 'icu_coasting_time', 'coasting_secs')


def main():
    newest = date.today()
    oldest = newest - timedelta(days=DAYS)
    r = api_get(f'{BASE}/activities', auth=AUTH,
                params={'oldest': str(oldest), 'newest': str(newest), 'limit': 600})
    if not r or r.status_code != 200:
        print("API-fejl", getattr(r, 'status_code', 'n/a'))
        return 1

    acts = [a for a in (r.json() or []) if a.get('type') in BIKE_TYPES]
    lines = []
    lines.append(f"Cykel-EF audit · {newest} · {len(acts)} cykelpas i {DAYS} dage")
    lines.append("")

    # Hvilke coasting-felter findes overhovedet? Feltnavne skal verificeres,
    # ikke antages -- samme fælde som bodyFat vs. Kropsfedt.
    seen = set()
    for a in acts:
        for k in a:
            if 'coast' in k.lower():
                seen.add(k)
    lines.append(f"Coasting-felter fundet i API: {sorted(seen) or 'INGEN'}")
    lines.append(f"Alle feltnavne paa foerste pas: {sorted(acts[0].keys()) if acts else '-'}")
    lines.append("")
    lines.append(f"{'dato':11} {'inde':5} {'min':>4} {'EF':>6} {'VI':>5} {'hm/km':>6} "
                 f"{'hard%':>6} {'coast%':>7}  navn")
    lines.append("-" * 100)

    for a in sorted(acts, key=lambda x: (x.get('start_date_local') or '')):
        dt = (a.get('start_date_local') or '')[:10]
        mins = round((a.get('moving_time') or 0) / 60)
        indoor = bool(a.get('trainer')) or a.get('type') == 'VirtualRide'
        ef = a.get('icu_efficiency_factor')
        np_ = a.get('icu_weighted_avg_watts') or a.get('normalized_watts')
        avg = a.get('average_watts')
        vi = round(np_ / avg, 3) if (np_ and avg) else None
        km = (a.get('distance') or 0) / 1000.0
        hmkm = round((a.get('total_elevation_gain') or 0) / km, 1) if km > 0 else None
        hf = _hard_fraction(a)
        coast = None
        for k in COAST_KEYS:
            if a.get(k) is not None and (a.get('moving_time') or 0) > 0:
                coast = round(a[k] / a['moving_time'] * 100, 1)
                break
        f = lambda v, w, d=2: (f"{v:>{w}.{d}f}" if isinstance(v, (int, float)) else f"{'-':>{w}}")
        lines.append(
            f"{dt:11} {'INDE' if indoor else 'ude ':5} {mins:>4} {f(ef,6,3)} {f(vi,5,2)} "
            f"{f(hmkm,6,1)} {f(hf*100 if hf is not None else None,6,1)} {f(coast,7,1)}  "
            f"{(a.get('name') or '')[:40]}"
        )

    os.makedirs('debug', exist_ok=True)
    with open('debug/bike_ef_audit.txt', 'w', encoding='utf-8') as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:6]))
    print(f"... skrevet {len(lines)} linjer til debug/bike_ef_audit.txt")
    return 0


if __name__ == '__main__':
    sys.exit(main())
