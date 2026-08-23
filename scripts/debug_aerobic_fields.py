"""Diagnose runde 3: koer aerobic.py mod live data og vis den faktiske EF-serie."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from modules.aerobic import get_ef_history

res = get_ef_history(days=180)
if not res:
    print("INGEN DATA"); sys.exit(1)
for disc in ('run', 'bike'):
    pts = res['history'][disc]
    print(f"\n=== {disc.upper()} — {len(pts)} punkter")
    for p in pts:
        print(f"  {p['date']}  EF={p['v']:.3f}  {p['mins']:4d} min  HR={p['hr']}  {p['name'][:40]}")
    print(f"  TREND: {json.dumps(res['trend'][disc], ensure_ascii=False)}")
