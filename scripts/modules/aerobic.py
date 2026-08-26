"""Aerob effektivitet (Efficiency Factor) — formsignal mellem tærskeltests.

EF svarer på ét spørgsmål: *bliver jeg hurtigere ved samme puls?* Til forskel
fra CTL (som kun måler hvor meget arbejde der er lagt ind) og fra Garmins
VO2max-estimat (som stiger mekanisk når vægten falder, fordi det er ml/kg/min).

To discipliner, to forskellige kilder — verificeret mod rådata 23/8-2026:

  LØB   Intervals udfylder IKKE icu_efficiency_factor uden power (0/35 løb).
        Beregnes derfor selv som gap * 60 / gns.puls = meter pr. minut pr.
        hjerteslag. `gap` (grade adjusted pace) er udfyldt 35/35 og korrigerer
        for stigning — Bergen 23/8 havde average_speed 2,37 m/s men gap 3,04.
        Uden GAP ville hvert bakkeløb se ud som formtab.

  CYKEL Intervals' eget icu_efficiency_factor (NP/puls) genbruges, men KUN på
        hometrainer. Rådata viste EF 0,90–1,16 på Mallorca-bjergture mod
        1,48–1,60 indendørs i samme periode — forskellen er coasting og
        nedkørsler, ikke form. Udendørs EF på varieret terræn er støj.

Filtrene er bevidst hårde. Et EF-tal fra et forkert pas er værre end ingen
tal, fordi det ligner data.
"""
from datetime import date, timedelta

from .config import BASE, AUTH, api_get

RUN_TYPES  = ('Run', 'TrailRun', 'VirtualRun')
BIKE_TYPES = ('Ride', 'VirtualRide', 'GravelRide')

MIN_RUN_SECS   = 35 * 60   # kortere pas domineres af opvarmning
MIN_BIKE_SECS  = 40 * 60
MAX_HM_PER_KM  = 15.0      # GAP underkorrigerer på stejlt terræn (Fornalutx ~20-25)
MAX_HARD_FRAC  = 0.10      # >10 % af tiden i HR-zone 4+ = ikke et aerobt pas
TREND_WINDOW   = 42        # dage — samme horisont som CTL's tidskonstant
MIN_SAMPLES    = 3         # under dette er medianen ikke et signal


def _hard_fraction(act):
    """Andel af tiden i HR-zone 4 og opefter.

    Skiller aerobe pas fra intervalpas uden at stole på icu_intensity, som
    ikke duer til formålet: hans lange Z2-løb ligger på IF 84-88, altså i
    samme leje som VO2-passene. Zonetiderne skiller dem rent.
    """
    zt = act.get('icu_hr_zone_times')
    if not zt or not isinstance(zt, list) or len(zt) < 4:
        return None
    total = sum(z or 0 for z in zt)
    if total <= 0:
        return None
    return sum(z or 0 for z in zt[3:]) / total


def _is_aerobic(act):
    """True hvis passet er aerobt nok til at EF er sammenligneligt."""
    hf = _hard_fraction(act)
    if hf is not None:
        return hf < MAX_HARD_FRAC
    # Fallback når zonetider mangler (3/183 pas): IF som grov si
    intensity = act.get('icu_intensity')
    return intensity is not None and intensity < 85


def run_ef(act):
    """EF for ét løb: meter pr. minut pr. hjerteslag, stigningskorrigeret.

    Returnerer None hvis passet ikke kvalificerer.
    """
    if act.get('type') not in RUN_TYPES:
        return None
    if act.get('race'):
        return None
    if (act.get('moving_time') or 0) < MIN_RUN_SECS:
        return None

    gap = act.get('gap')
    hr = act.get('average_heartrate')
    if not gap or not hr or hr < 60:
        return None

    km = (act.get('distance') or 0) / 1000.0
    if km <= 0:
        return None
    hm_per_km = (act.get('total_elevation_gain') or 0) / km
    if hm_per_km > MAX_HM_PER_KM:
        return None

    if not _is_aerobic(act):
        return None

    return round(gap * 60.0 / hr, 3)


def bike_ef(act):
    """EF for ét cykelpas — kun hometrainer, hvor tallet er sammenligneligt."""
    if act.get('type') not in BIKE_TYPES:
        return None
    if act.get('race'):
        return None
    if (act.get('moving_time') or 0) < MIN_BIKE_SECS:
        return None

    indoor = bool(act.get('trainer')) or act.get('type') == 'VirtualRide'
    if not indoor:
        return None

    ef = act.get('icu_efficiency_factor')
    if not ef:
        return None
    if not _is_aerobic(act):
        return None

    return round(float(ef), 3)


def _median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    mid = n // 2
    return s[mid] if n % 2 else round((s[mid - 1] + s[mid]) / 2, 3)


def build_points(acts):
    """Omsæt rå aktiviteter til EF-punkter pr. disciplin, kronologisk."""
    out = {'run': [], 'bike': []}
    for a in acts or []:
        dt = (a.get('start_date_local') or '')[:10]
        if not dt:
            continue
        for disc, fn in (('run', run_ef), ('bike', bike_ef)):
            ef = fn(a)
            if ef is None:
                continue
            out[disc].append({
                'date':  dt,
                'v':     ef,
                'real':  True,
                'mins':  round((a.get('moving_time') or 0) / 60),
                'hr':    a.get('average_heartrate'),
                'name':  (a.get('name') or '')[:60],
                'id':    a.get('id'),
            })
    for disc in out:
        out[disc].sort(key=lambda p: p['date'])
    return out


def trend(points, today=None, window=TREND_WINDOW):
    """Median i de seneste `window` dage vs. de `window` dage før det.

    Median frem for gennemsnit: ét pas i 30 graders varme eller med et fladt
    batteri i pulsbæltet skal ikke flytte kurven.
    """
    today = today or date.today()
    cut1 = today - timedelta(days=window)
    cut2 = today - timedelta(days=window * 2)

    now_vals, prev_vals = [], []
    for p in points or []:
        try:
            d = date.fromisoformat(p['date'])
        except (ValueError, KeyError, TypeError):
            continue
        if d > cut1:
            now_vals.append(p['v'])
        elif d > cut2:
            prev_vals.append(p['v'])

    now = _median(now_vals) if len(now_vals) >= MIN_SAMPLES else None
    prev = _median(prev_vals) if len(prev_vals) >= MIN_SAMPLES else None
    pct = round((now - prev) / prev * 100, 1) if (now and prev) else None

    return {
        'current': now,
        'previous': prev,
        'pct': pct,
        'n': len(now_vals),
        'n_prev': len(prev_vals),
        'window': window,
        'thin': len(now_vals) < MIN_SAMPLES,
    }


def get_ef_history(days=180):
    """Hent aktiviteter og byg EF-historik + trend pr. disciplin.

    Returnerer {'history': {...}, 'trend': {...}, 'acts': [...]} eller None ved API-fejl,
    så kalderen kan beholde eksisterende data frem for at nulstille den.
    """
    newest = date.today()
    oldest = newest - timedelta(days=days)
    r = api_get(f'{BASE}/activities', auth=AUTH,
                params={'oldest': str(oldest), 'newest': str(newest), 'limit': 600})
    if not r or r.status_code != 200:
        print(f"  EF: /activities -> HTTP {getattr(r, 'status_code', 'n/a')}, springer over")
        return None

    acts = r.json() or []
    pts = build_points(acts)
    tr = {disc: trend(pts[disc], today=newest) for disc in pts}
    print(f"  EF: løb {len(pts['run'])} pkt (trend {tr['run']['current']}), "
          f"cykel {len(pts['bike'])} pkt (trend {tr['bike']['current']})")
    # 'acts' følger med ud, så decoupling.py kan læse temperatur og starttidspunkt
    # på det seneste pas uden at hente /activities en gang til.
    return {'history': pts, 'trend': tr, 'acts': acts}
