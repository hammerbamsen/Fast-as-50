# -*- coding: utf-8 -*-
"""Outlook-tider (blok 8, 8/9-2026) — ÉN kilde for hvornår pas lægges i kalenderen.

Bruges af både .github/workflows/scripts/sync_outlook.py (ugesynk fra
Intervals-events) og scripts/apply_edit.py (plan-edit, entries fra plan.json).

Regel: styrke starter 06:30. Ved flere pas samme dag: styrke først (medmindre
timeOverrides siger andet), hvert efterfølgende pas starter ved forrige slut
+ 15 min (slut = start + moving_time, min 30 min). To pas må ALDRIG overlappe.
timeOverrides fra plan.json gælder stadig for det enkelte pas; giver en
override overlap, flyttes det pas UDEN override.

Ren logik — ingen env, ingen netværk. Tests: test_outlook_times.py.
"""
from datetime import date, datetime, timedelta

TYPE_EMOJI = {
    'Run': '🏃', 'Ride': '🚴', 'Swim': '🏊',
    'WeightTraining': '💪', 'Walk': '🚶',
    # Manglede -> faldt tilbage til vaegtstang paa alle OW-svom (28/7-2026)
    'OpenWaterSwim': '🏊', 'VirtualRide': '🚴', 'VirtualRun': '🏃',
    'TrailRun': '🏃', 'Hike': '🥾', 'Gravel Ride': '🚴',
}
STRENGTH_TYPES = ('WEIGHTTRAINING', 'WEIGHT_TRAINING', 'WEIGHTS', 'WORKOUT', 'STRENGTH')
START_HOUR = {
    'SWIM': (6, 0), 'OW': (6, 0), 'OPENWATERSWIM': (6, 0),
    'RUN': (6, 30), 'TRAIL_RUN': (6, 30),
    'RIDE': (7, 0), 'VIRTUAL_RIDE': (7, 0),
    'WEIGHTTRAINING': (6, 30), 'WEIGHT_TRAINING': (6, 30), 'WEIGHTS': (6, 30),
    'WORKOUT': (6, 30), 'STRENGTH': (6, 30),
}
DEFAULT_START = (6, 0)
GAP_MIN = 15          # minutter mellem to pas
MIN_DUR_MIN = 30      # et pas fylder mindst 30 min i kalenderen


def is_strength(wtype):
    return (wtype or '').upper() in STRENGTH_TYPES


def default_start(wtype):
    return START_HOUR.get((wtype or '').upper(), DEFAULT_START)


def override_for(day_override, wtype):
    """(h, m) fra dagens override — dict slår op pr. disciplin (lowercase),
    tuple/liste gælder alle pas den dag. None uden override."""
    if isinstance(day_override, dict):
        hit = day_override.get((wtype or '').lower())
        return tuple(hit) if hit else None
    if day_override:
        return tuple(day_override)
    return None


def _duration(w):
    """Varighed i kalenderen: moving_time rundet op til hele minutter, mindst
    MIN_DUR_MIN; uden moving_time 60 min (som før)."""
    try:
        secs = int(w.get('moving_time') or 0)
    except (TypeError, ValueError):
        secs = 0
    mins = (secs + 59) // 60 if secs > 0 else 60
    return timedelta(minutes=max(MIN_DUR_MIN, mins))


def _day_of(workouts):
    for w in workouts:
        s = (w.get('start_date_local') or '')[:10]
        try:
            return date.fromisoformat(s)
        except ValueError:
            continue
    return date.today()


def _conflicts(start, end, placed):
    """(start, slut) på det første placerede pas der overlapper [start, slut) — ellers None."""
    for _w, s, e in placed:
        if start < e and end > s:
            return (s, e)
    return None


def _push_past(start, dur, placed):
    """Skub starten frem til første hul: forrige slut + GAP_MIN, indtil intet overlap."""
    c = _conflicts(start, start + dur, placed)
    while c:
        start = c[1] + timedelta(minutes=GAP_MIN)
        c = _conflicts(start, start + dur, placed)
    return start


def schedule_day(workouts, overrides):
    """[(workout, start_dt)] sorteret efter starttid for ÉN dags workouts
    (Intervals-events: type, moving_time, start_date_local). overrides er
    dagens timeOverride: (h, m) | {disciplin: (h, m)} | None."""
    day = _day_of(workouts)
    fixed, free = [], []
    for w in workouts:
        ov = override_for(overrides, w.get('type'))
        if ov:
            fixed.append((w, ov))
        else:
            free.append(w)
    # Faste pas (override) først, i tidsorden (styrke først ved samme tid).
    # Overlapper to faste (fx dagsdækkende override), taber det senere sin
    # plads og skubbes til første hul efter det pas det stødte på.
    fixed.sort(key=lambda t: (t[1], not is_strength(t[0].get('type'))))
    placed = []
    demoted = []
    for w, (h, m) in fixed:
        start = datetime(day.year, day.month, day.day, h, m)
        if _conflicts(start, start + _duration(w), placed):
            demoted.append((w, start))
        else:
            placed.append((w, start, start + _duration(w)))
    for w, start in demoted:
        dur = _duration(w)
        start = _push_past(start, dur, placed)
        placed.append((w, start, start + dur))
    # Frie pas: styrke først, derefter i standard-starttidsorden (stabilt).
    # Første frie pas starter på sin standardtid, hvert efterfølgende ved
    # forrige slut + GAP_MIN — og altid skubbet forbi faste pas.
    free.sort(key=lambda w: (not is_strength(w.get('type')), default_start(w.get('type'))))
    cursor = None
    for w in free:
        h, m = default_start(w.get('type'))
        start = datetime(day.year, day.month, day.day, h, m)
        if cursor is not None:
            start = cursor + timedelta(minutes=GAP_MIN)
        dur = _duration(w)
        start = _push_past(start, dur, placed)
        placed.append((w, start, start + dur))
        cursor = start + dur
    placed.sort(key=lambda t: t[1])
    return [(w, s) for w, s, _e in placed]


def event_body(w, start_dt):
    """Graph-event for et pas med beregnet starttid."""
    name = w.get('name', 'Træning')
    wtype = w.get('type', 'Run')
    desc = w.get('description', '')
    emoji = TYPE_EMOJI.get(wtype, '🏋')
    end_dt = start_dt + _duration(w)
    return {
        'subject': f'{emoji} {name}',
        'body': {'contentType': 'text', 'content': desc or f'Fast as Fifty - {wtype}'},
        'start': {'dateTime': start_dt.strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': 'Europe/Copenhagen'},
        'end':   {'dateTime': end_dt.strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': 'Europe/Copenhagen'},
        'categories': ['Træning'],
        'showAs': 'busy',
        'isReminderOn': True,
        'reminderMinutesBeforeStart': 30,
    }


def normalize_overrides(raw):
    """plan.athletes.kennet.timeOverrides -> {dato: (h, m) | {disciplin_lower: (h, m)}}
    (samme normalisering som build_workouts.py)."""
    out = {}
    for k, v in (raw or {}).items():
        out[k] = ({s.lower(): tuple(t) for s, t in v.items()}
                  if isinstance(v, dict) else tuple(v))
    return out


def workouts_from_entries(day_iso, entries):
    """plan.json-entries -> workout-dicts som schedule_day forstår (kun pas med workout)."""
    out = []
    for e in (entries or []):
        wo = e.get('workout')
        if wo:
            out.append({**wo, 'start_date_local': f'{day_iso}T00:00:00'})
    return out
