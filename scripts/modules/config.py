"""Fælles konfiguration, konstanter og hjælpefunktioner."""
import os, time, requests

API_KEY       = os.environ.get('INTERVALS_API_KEY', '')
ATHLETE_ID    = os.environ.get('INTERVALS_ATHLETE_ID', 'i0')
GH_TOKEN      = os.environ.get('GH_TOKEN', '')
ANTHROPIC_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
REPO          = 'hammerbamsen/fast-as-50'
BASE          = f'https://intervals.icu/api/v1/athlete/{ATHLETE_ID}'
AUTH          = ('API_KEY', API_KEY)

# ── Goal Engine: al plan-data læses fra data/plan.json ─────────
# plan.json er den ENESTE kilde til CTL-plan, blok-typer, racedatoer,
# programstart og mål. Det AKTIVE program vælges efter dagens dato via
# modules/programs.py (start <= i dag <= end, ellers seneste startede) —
# der er ingen hardkodet programlængde nogen steder i koden.
# Hardcodede fallbacks bruges kun hvis filen mangler.
import json as _json
from datetime import date as _date, timedelta as _timedelta
from . import programs as _programs

_PLAN_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'plan.json')

def _load_plan():
    try:
        with open(_PLAN_PATH, encoding='utf-8') as f:
            return _json.load(f)
    except Exception as e:
        print(f"  ⚠️  plan.json kunne ikke læses ({e}) — bruger fallback-konstanter")
        return None

PLAN = _load_plan()
ACTIVE_PROGRAM = _programs.active_program(PLAN, "kennet") if PLAN else None

if ACTIVE_PROGRAM:
    PROGRAM_ID  = ACTIVE_PROGRAM['id']
    CTL_PLAN    = _programs.ctl_plan(ACTIVE_PROGRAM)
    BLOCK_TYPES = _programs.block_types(ACTIVE_PROGRAM)
    TOTAL_WEEKS = ACTIVE_PROGRAM['totalWeeks']
    PLAN_START  = _date.fromisoformat(ACTIVE_PROGRAM['start'])
    RACES       = ACTIVE_PROGRAM.get('races', [])
    GOALS       = ACTIVE_PROGRAM.get('goals', {})
    # Løb i SENERE programmer (til nedtælling på dashboardet). Kommende løb
    # på tværs af alle programmer: programs.upcoming_races(PLAN, "kennet").
    NEXT_RACES  = [r for p in _programs.programs_for(PLAN, "kennet")
                   if p['start'] > ACTIVE_PROGRAM['start']
                   for r in p.get('races', [])]
else:
    # Fallback (bør aldrig rammes i drift)
    PROGRAM_ID  = 'fallback'
    CTL_PLAN    = [34, 36, 38, 41, 48, 50, 54, 60, 56, 61, 67, 63, 59, 56]
    BLOCK_TYPES = {1:'BUILD',2:'BUILD+',3:'BUILD+',4:'RECOVERY',5:'BUILD',6:'BUILD',
                   7:'BUILD',8:'BUILD+',9:'RECOVERY',10:'BUILD',11:'BUILD+',12:'TAPER',
                   13:'TAPER',14:'RACE'}
    TOTAL_WEEKS = 14
    PLAN_START  = _date(2026, 6, 1)
    RACES       = [{"name": "Christiansborg Rundt", "date": "2026-08-29"},
                   {"name": "Marathon du Médoc", "date": "2026-09-05"}]
    NEXT_RACES  = []
    GOALS       = {"weightKg": 68, "bodyFatPct": 16, "afDaysPerWeek": 5}
    ACTIVE_PROGRAM = {
        'id': PROGRAM_ID, 'name': 'Fast as Fifty', 'athletes': ['kennet'],
        'start': PLAN_START.isoformat(), 'totalWeeks': TOTAL_WEEKS,
        'end': (PLAN_START + _timedelta(days=TOTAL_WEEKS * 7 - 1)).isoformat(),
        'philosophy': 'capacity', 'description': '',
        'weeks': [{'week': w, 'blockType': BLOCK_TYPES[w], 'ctlTarget': CTL_PLAN[w - 1]}
                  for w in range(1, TOTAL_WEEKS + 1)],
        'races': RACES, 'goals': GOALS,
    }

# Projektstart = første programs start (AF-log og andre "siden projektstart"-
# serier spænder over ALLE programmer, ikke kun det aktive).
PROJECT_START = min((_date.fromisoformat(p['start']) for p in _programs.programs_for(PLAN, 'kennet')),
                    default=PLAN_START) if PLAN else PLAN_START

# Faste programmål -- én kilde, brugt i både dashboard-KPI'er og coach-tekst.
# CTL-start/slutmål udledes ALTID af CTL_PLAN, så de aldrig kan komme ud af sync med planen.
CTL_START = CTL_PLAN[0]
CTL_GOAL = CTL_PLAN[-1]
AF_GOAL = GOALS.get("afDaysPerWeek", 5)
SLEEP_GOAL_HOURS = 7
# Svøm-/løbemål er PROGRAM-specifikke og findes kun i programmets goals
# (medoc-2026: swimMeters/runKmPerWeek; tds-2027: ingen -> KPI'en vises uden mål).
# Brug GOALS.get('swimMeters') / GOALS.get('runKmPerWeek') direkte.

def athlete_age(today=None, athlete='kennet'):
    """Alder beregnet ved kørsel fra athletes.<a>.birthYear i plan.json.
    None hvis feltet mangler — prompter udelader så alderen frem for at gætte."""
    today = today or _date.today()
    by = ((PLAN or {}).get('athletes', {}).get(athlete) or {}).get('birthYear')
    return (today.year - int(by)) if by else None


DK_DAYS    = ["Mandag","Tirsdag","Onsdag","Torsdag","Fredag","Lørdag","Søndag"]
DAY_SHORT  = ["Man","Tir","Ons","Tor","Fre","Lør","Søn"]
DK_MONTHS  = ["jan","feb","mar","apr","maj","jun","jul","aug","sep","okt","nov","dec"]

# (BLOCK_TYPES defineres ovenfor af Goal Engine / plan.json)

# Friel-baserede løb-pace-zoner (sek/km). Tærsklen læses fra plan.json
# (thresholdSec) -- ingen fast værdi hardcodet her.
# VIGTIGT: Intervals.icu's egen pace_zone_times bruger en generisk 7-zone
# %-tabel der IKKE matcher disse grænser for Z3 og opefter (verificeret
# 2/7-26 -- se sessions.py: compute_run_pace_zone_secs).
# Z2 matcher tilfældigvis ICU's egen tabel, men Z3-Z6 gør ikke -- derfor
# beregnes løb-zone-tid altid ud fra rå pace-stream mod DISSE grænser.
# UDLEDES nu af plan.json -> athletes.kennet.zones (28/7-2026).
# thresholdSec + runPct er eneste kilde. Ren matematik:
#   hurtigste = ceil(thr*100/hi)    langsomste = ceil(thr*100/lo)-1
# Ændrer du threshold i plan.json, følger disse grænser automatisk med.
import math as _math

def _derive_run_pace_zones():
    z = ((PLAN or {}).get('athletes', {}).get('kennet', {}) or {}).get('zones') or {}
    thr, pct = z.get('thresholdSec'), z.get('runPct')
    if not thr or not pct:
        return None
    def _fast(p):
        return _math.ceil(thr * 100 / p)
    out = {}
    for name, band in pct.items():
        lo, hi = band[0], band[1]
        if lo is None:
            out[name] = (_fast(hi), 99999)
        elif hi is None:
            out[name] = (0, _fast(lo) - 1)
        else:
            out[name] = (_fast(hi), _fast(lo) - 1)
    return out

RUN_PACE_ZONES_SEC_PER_KM = _derive_run_pace_zones() or {
    # Fallback — kun hvis plan.json mangler zones-blokken.
    'Z1': (334, 99999),
    'Z2': (296, 333),
    'Z3': (266, 295),
    'Z4': (253, 265),
    'Z5': (233, 252),
    'Z6': (0, 232),
}


def _derive_bike_zone_watts():
    """(lo, hi) watt pr. zone, udledt af ftpW + bikePct i plan.json.

    Samme princip som løbezonerne: plan.json er eneste kilde, så en FTP-test
    slår automatisk igennem. Bruges til rep-for-rep-vurdering af
    cykelintervaller.
    """
    z = ((PLAN or {}).get('athletes', {}).get('kennet', {}) or {}).get('zones') or {}
    ftp, pct = z.get('ftpW'), z.get('bikePct')
    if not ftp or not pct:
        return {}
    out = {}
    for name, band in pct.items():
        lo, hi = band[0], band[1]
        out[name] = (
            int(round(ftp * lo / 100)) if lo is not None else 0,
            int(round(ftp * hi / 100)) if hi is not None else 99999,
        )
    return out


BIKE_ZONES_WATTS = _derive_bike_zone_watts()


def api_get(url, auth=None, params=None, timeout=20, retries=3):
    """requests.get med exponential backoff retry på transiente fejl."""
    for attempt in range(retries):
        try:
            r = requests.get(url, auth=auth, params=params, timeout=timeout)
            if r.status_code < 500:
                return r
            print(f"  ⚠️  api_get {url} → HTTP {r.status_code}, forsøg {attempt+1}/{retries}")
        except (requests.ConnectionError, requests.Timeout) as e:
            print(f"  ⚠️  api_get {url} → {e}, forsøg {attempt+1}/{retries}")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    return None


def ctl_plan_for_week(week_num):
    idx = min(max(week_num, 1), len(CTL_PLAN)) - 1
    return CTL_PLAN[idx]


def fix_enc(s, max_passes=6):
    """Reparerer UTF-8-som-Latin-1 mojibake (fx 'Ã¦' -> 'æ', 'Â·' -> '·').
    Kører iterativt op til max_passes gange, da tekst kan være korrumperet
    i flere lag (set i praksis: 'all_weeks[N].focus' med op til 4 lag efter
    gentagne cache-pass-through cyklusser uden reparation).
    Stopper sikkert når: (a) et pass ikke ændrer noget (stabil/ren tekst),
    eller (b) encode fejler fordi teksten indeholder ægte Unicode-tegn
    uden for Latin-1 (fx —, ', ", som Kennets AI-tekster ofte bruger korrekt)
    -- så ægte specialtegn bliver ALDRIG fejlagtigt ødelagt."""
    if not isinstance(s, str) or not s:
        return s
    cur = s
    for _ in range(max_passes):
        try:
            nxt = cur.encode('latin-1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if nxt == cur:
            break
        cur = nxt
    return cur


def fmt(val, decimals=1):
    if val is None:
        return "—"
    try:
        return f"{float(val):.{decimals}f}".replace('.', ',')
    except (ValueError, TypeError):
        return str(val)


def color_for(val, target, lower=True):
    if val is None:
        return '#7A6A58'
    try:
        val = float(val)
        pct = val / target if target else 0
        if lower:
            if pct <= 1.0:   return '#27AE60'
            if pct <= 1.1:   return '#E67E22'
            return '#C0392B'
        else:
            if pct >= 0.95:  return '#27AE60'
            if pct >= 0.80:  return '#E67E22'
            return '#C0392B'
    except (ValueError, TypeError):
        return '#7A6A58'
