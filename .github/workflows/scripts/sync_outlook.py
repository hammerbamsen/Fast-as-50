import os, requests
from datetime import date, timedelta

CLIENT_ID     = os.environ['AZURE_CLIENT_ID']
TENANT_ID     = os.environ['AZURE_TENANT_ID']
CLIENT_SECRET = os.environ['AZURE_CLIENT_SECRET']
API_KEY       = os.environ['INTERVALS_API_KEY']
ATHLETE_ID    = os.environ.get('INTERVALS_ATHLETE_ID') or 'i599466'  # fallback: secret har vist sig tom
WEEK          = int(os.environ.get('WEEK', 2))
USER          = 'kennet@hammerby.com'
GRAPH         = f'https://graph.microsoft.com/v1.0/users/{USER}'
TIMEOUT       = 30

# PLAN_START/TOTAL_WEEKS laeses fra plan.json (rettet 28/8-2026 — var hardkodet
# til medoc-2026's 01-06-2026/14 uger, hvilket fik uge 15-16 til at fejle her).
import json as _json
_prog = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', 'data', 'plan.json'),
                        encoding='utf-8'))['program']
PLAN_START_D = date.fromisoformat(_prog['start'])
TOTAL_WEEKS  = _prog['totalWeeks']

assert 1 <= WEEK <= TOTAL_WEEKS, f'Ugyldig uge: {WEEK} (program har {TOTAL_WEEKS} uger)'

# Token
resp = requests.post(
    f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token',
    data={'grant_type':'client_credentials','client_id':CLIENT_ID,
          'client_secret':CLIENT_SECRET,'scope':'https://graph.microsoft.com/.default'},
    timeout=TIMEOUT
)
resp.raise_for_status()
token    = resp.json()['access_token']
hdrs     = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
hdrs_get = {k:v for k,v in hdrs.items() if k != 'Content-Type'}
print('Token OK')

plan_start = PLAN_START_D
week_start = plan_start + timedelta(weeks=WEEK-1)
week_end   = week_start + timedelta(days=6)
print(f'Uge {WEEK}: {week_start} til {week_end}')

# TRIN 1: Hent workouts fra Intervals FØRST.
# Rækkefølgen er kritisk: sletter vi før vi ved at der er noget at oprette,
# efterlader en Intervals-fejl kalenderen tom. Gælder især uovervåget cron-kørsel.
r = requests.get(
    f'https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/events',
    auth=('API_KEY', API_KEY),
    params={'oldest': f'{week_start}T00:00:00', 'newest': f'{week_end}T23:59:00',
            'category': 'WORKOUT'},
    timeout=TIMEOUT
)
if r.status_code != 200:
    print(f'FEJL: Intervals GET returnerede {r.status_code}: {r.text[:200]}')
    raise SystemExit(1)
workouts = r.json()
print(f'{len(workouts)} workouts fra Intervals')
if not workouts:
    print('FEJL: 0 workouts fra Intervals — forventede en planlagt uge. Afbryder.')
    raise SystemExit(1)

TYPE_EMOJI = {
    'Run': '🏃', 'Ride': '🚴', 'Swim': '🏊',
    'WeightTraining': '💪', 'Walk': '🚶',
    # Manglede -> faldt tilbage til vaegtstang paa alle OW-svom (28/7-2026)
    'OpenWaterSwim': '🏊', 'VirtualRide': '🚴', 'VirtualRun': '🏃',
    'TrailRun': '🏃', 'Hike': '🥾', 'Gravel Ride': '🚴',
}
START_HOUR = {
    'SWIM': (6, 0), 'OW': (6, 0), 'OPENWATERSWIM': (6, 0),
    'RUN': (6, 30), 'TRAIL_RUN': (6, 30),
    'RIDE': (7, 0), 'VIRTUAL_RIDE': (7, 0),
    'WEIGHTTRAINING': (7, 0), 'WEIGHT_TRAINING': (7, 0), 'WEIGHTS': (7, 0),
}

# Tidspunkt-overrides fra plan.json — SAMME kilde som build_workouts.py.
# Uden dette havde dette script sin egen tidstabel, og et pas flyttet til
# eftermiddagen i plan.json landede alligevel 06:30 i kalenderen (28/7-2026).
import json as _json

def _load_time_overrides():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in ('data/plan.json',
              os.path.join(here, '..', '..', '..', 'data', 'plan.json')):
        try:
            with open(p, encoding='utf-8') as f:
                raw = _json.load(f)['athletes']['kennet'].get('timeOverrides', {})
        except Exception:
            continue
        out = {}
        for k, v in raw.items():
            out[k] = ({s.lower(): tuple(t) for s, t in v.items()}
                      if isinstance(v, dict) else tuple(v))
        print(f'timeOverrides: {len(out)} dato(er) fra {p}')
        return out
    print('  ADVARSEL: timeOverrides kunne ikke laeses — bruger standardtider')
    return {}

TIME_OVERRIDES = _load_time_overrides()

def _start_for(dt, wtype):
    """dt er 'YYYY-MM-DD'. Dict-override slaar op pr. disciplin."""
    ov = TIME_OVERRIDES.get(dt)
    if isinstance(ov, dict):
        hit = ov.get((wtype or '').lower())
        if hit:
            return hit
    elif ov:
        return ov
    return START_HOUR.get((wtype or '').upper(), (6, 0))

# TRIN 2: Slet eksisterende Traening-events — først nu, hvor workouts er i hus
url    = f'{GRAPH}/calendarView'
params = {'startDateTime': f'{week_start}T00:00:00',
          'endDateTime':   f'{week_end}T23:59:59',
          '$select': 'id,subject,categories', '$top': '50'}
existing = []
while url:
    r = requests.get(url, headers=hdrs_get, params=params, timeout=TIMEOUT)
    params = None
    body   = r.json()
    existing.extend(body.get('value', []))
    url = body.get('@odata.nextLink')

deleted = 0
for e in existing:
    if any(c in ('Træning', 'Traening') for c in e.get('categories', [])):
        dr = requests.delete(f'{GRAPH}/events/{e["id"]}', headers=hdrs, timeout=TIMEOUT)
        if dr.status_code in (204, 404):
            print(f'  Slettet: {e["subject"]}')
            deleted += 1
        else:
            print(f'  FEJL slet {e["subject"]}: {dr.status_code}')
print(f'Slettet: {deleted}')

# TRIN 3: Opret nye events
ok = err = 0
for w in workouts:
    dt    = w.get('start_date_local', '')[:10]
    name  = w.get('name', 'Træning')
    wtype = w.get('type', 'Run')
    dur   = w.get('moving_time') or 3600
    desc  = w.get('description', '')
    emoji = TYPE_EMOJI.get(wtype, '🏋')
    sh, sm = _start_for(dt, wtype)
    end_min = sh * 60 + sm + dur // 60
    eh, em  = end_min // 60, end_min % 60
    event = {
        'subject': f'{emoji} {name}',
        'body': {'contentType': 'text', 'content': desc or f'Fast as Fifty - {wtype}'},
        'start': {'dateTime': f'{dt}T{sh:02d}:{sm:02d}:00', 'timeZone': 'Europe/Copenhagen'},
        'end':   {'dateTime': f'{dt}T{eh:02d}:{em:02d}:00', 'timeZone': 'Europe/Copenhagen'},
        'categories': ['Træning'],
        'showAs': 'busy',
        'isReminderOn': True,
        'reminderMinutesBeforeStart': 30,
    }
    resp = requests.post(f'{GRAPH}/events', headers=hdrs, json=event, timeout=TIMEOUT)
    if resp.status_code == 201:
        print(f'  Oprettet: {dt} {emoji} {name}')
        ok += 1
    else:
        print(f'  FEJL opret {dt} {name}: {resp.status_code} {resp.text[:120]}')
        err += 1

print(f'Oprettet: {ok} | Fejl: {err}')
if err > 0:
    raise SystemExit(1)
print('DONE')
