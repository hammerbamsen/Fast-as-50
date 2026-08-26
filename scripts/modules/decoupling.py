# -*- coding: utf-8 -*-
"""Decoupling — flagger ÉT aerobt pas der kostede for meget puls.

`aerobic.py` svarer på "hvordan går det over 42 dage". Dette modul svarer på
"hvad skete der i går". Begge bruger nøjagtig samme EF-tal (`run_ef`/`bike_ef`)
— forskellen er horisonten, ikke metoden. Der beregnes intet nyt her.

Baggrund (25/8-2026). "Løb Z2 18 km" blev kørt på 5:16/km ved 151 i snit.
Fem dage før: shakeout på 5:13/km ved 140. En uge før: 26 km på 5:05/km ved
145. EF faldt fra ~1,36 til ~1,27, altså ca. 6,5 %. Intet på dashboardet
reagerede, fordi TSS ramte planen (110) og morgen-wellness var grøn.
Belastningen var rigtig. Intensiteten var forkert. Ingen regel så på pulsen
INDE i passet.

Punkterne fandtes allerede i `data.json` under `efHistory` — ét punkt pr.
kvalificeret pas. De blev bare aldrig læst enkeltvis, kun som median over 42
dage, som ét enkelt pas per definition ikke kan flytte. Modulet her tilføjer
ingen datakilde; det læser den sidste værdi i en serie der allerede var der.

To ting bliver bevidst IKKE fjernet automatisk:

  VARME   Temperatur og starttidspunkt hænges PÅ flaget som kontekst, men
          trækkes aldrig fra tallet. 25/8 startede 14:56 — det eneste
          eftermiddagsløb i perioden, resten lå 06:30-08:00. Varme koster
          reelt 5-10 slag, men en automatisk korrektion ville være opfundet
          præcision. Coachen skal se begge dele og sige begge dele.

  ÉT PAS  Et flag er en observation om ét pas, ikke en formdiagnose. Tre
          dårlige pas i træk er en trend, og trends hører til i
          `aerobic.trend()`. Dette modul påstår aldrig andet end "det her
          pas var dyrere end dine egne sammenlignelige pas".

Filtrene arves fra aerobic.py og er med vilje hårde: kvalificerer passet ikke
til et EF-tal, siger modulet ingenting frem for at gætte.
"""
from datetime import date, timedelta

from .aerobic import run_ef, bike_ef, _median, TREND_WINDOW

# Under dette falder EF nok til at det er værd at nævne. EF-støjen mellem to
# sammenlignelige Z2-løb ligger erfaringsmæssigt på 2-3 % (18/8: 1,360 mod
# 23/8 Bergen: 1,361), så 5 % ligger klart uden for dagsvariationen.
NOTICE_PCT = -5.0
STRONG_PCT = -8.0

BASELINE_WINDOW = TREND_WINDOW   # 42 dage — samme horisont som EF-trenden
MIN_BASELINE    = 3              # under dette er medianen ikke et signal

# Varme og tidspunkt er kontekst, ikke korrektion.
WARM_TEMP_C    = 18.0
AFTERNOON_HOUR = 12

RUN_DISC, BIKE_DISC = 'run', 'bike'


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None      # NaN ud


def session_temp(act):
    """Temperatur i °C, hvis Intervals har den.

    Feltnavnet varierer med hvilken kilde der uploadede passet (Garmin lægger
    den i average_temp, vejr-berigelsen i icu_weather_temp), så alle kendte
    varianter prøves. None betyder "ved det ikke" — ikke "det var koldt".
    """
    for key in ('average_temp', 'icu_weather_temp', 'weather_temp', 'temperature'):
        t = _num((act or {}).get(key))
        if t is not None:
            return round(t, 1)
    return None


def start_hour(act):
    """Time (0-23) fra start_date_local. None hvis feltet mangler/er skævt."""
    s = (act or {}).get('start_date_local') or ''
    try:
        return int(s[11:13])
    except (ValueError, IndexError):
        return None


def session_ef(act):
    """(disciplin, EF) for passet — eller (None, None) hvis det ikke kvalificerer."""
    ef = run_ef(act)
    if ef is not None:
        return RUN_DISC, ef
    ef = bike_ef(act)
    if ef is not None:
        return BIKE_DISC, ef
    return None, None


def baseline_ef(points, before, window=BASELINE_WINDOW, min_n=MIN_BASELINE):
    """Median-EF for pas i de `window` dage FØR `before` — passet selv ekskluderet.

    Strengt "før": et pas må ikke være med til at definere den baseline det
    måles imod, ellers trækker et dårligt pas sin egen målestok med ned og
    underdriver afvigelsen.
    """
    try:
        ref = date.fromisoformat(before) if isinstance(before, str) else before
    except (ValueError, TypeError):
        return None, 0
    cut = ref - timedelta(days=window)

    vals = []
    for p in points or []:
        try:
            d = date.fromisoformat(p['date'])
        except (ValueError, KeyError, TypeError):
            continue
        if cut <= d < ref:
            v = _num(p.get('v'))
            if v is not None:
                vals.append(v)

    if len(vals) < min_n:
        return None, len(vals)
    return _median(vals), len(vals)


def _level(pct):
    if pct is None:
        return 'ok'
    if pct <= STRONG_PCT:
        return 'strong'
    if pct <= NOTICE_PCT:
        return 'notice'
    return 'ok'


def evaluate(act, points, window=BASELINE_WINDOW, min_n=MIN_BASELINE):
    """Vurder ét pas mod dets egen disciplins seneste EF-median.

    Returnerer None hvis passet ikke kan sammenlignes (forkert type, for
    kort, for stejlt, for hårdt, manglende puls/GAP, eller for tynd baseline).
    Ellers en dict — også når alt er fint, så kalderen kan vise "grøn" lige så
    let som "rød".
    """
    disc, ef = session_ef(act)
    if disc is None:
        return None

    day = (act.get('start_date_local') or '')[:10]
    if not day:
        return None

    base, n = baseline_ef((points or {}).get(disc), day, window=window, min_n=min_n)
    if base is None:
        return None

    pct = round((ef - base) / base * 100, 1)
    hour = start_hour(act)
    temp = session_temp(act)
    level = _level(pct)

    return {
        'date':        day,
        'discipline':  disc,
        'name':        (act.get('name') or '')[:60],
        'id':          act.get('id'),
        'ef':          ef,
        'baseline':    base,
        'pct':         pct,
        'n_baseline':  n,
        'level':       level,
        'flagged':     level != 'ok',
        'avg_hr':      act.get('average_heartrate'),
        'start_hour':  hour,
        'temp_c':      temp,
        'afternoon':   hour is not None and hour >= AFTERNOON_HOUR,
        'warm':        temp is not None and temp >= WARM_TEMP_C,
        # Sættes af latest(): var baseline-passene lagt på samme tid af døgnet?
        'time_of_day_comparable': None,
    }


def latest(acts, points, today=None, max_age_days=2,
           window=BASELINE_WINDOW, min_n=MIN_BASELINE):
    """Vurder det nyeste kvalificerede pas inden for `max_age_days`.

    Kun det nyeste: coachen taler om i går, ikke om hele ugen. Er der ikke
    kommet et sammenligneligt pas ind, returneres None og coachen tier — det
    er den rigtige opførsel, ikke en mangel.
    """
    today = today or date.today()
    cut = today - timedelta(days=max_age_days)

    dated = []
    for a in acts or []:
        day = (a.get('start_date_local') or '')[:10]
        if not day:
            continue
        try:
            d = date.fromisoformat(day)
        except ValueError:
            continue
        if cut <= d <= today:
            dated.append((day, a))
    dated.sort(key=lambda x: x[0], reverse=True)

    for _, a in dated:
        res = evaluate(a, points, window=window, min_n=min_n)
        if res is not None:
            res['time_of_day_comparable'] = _tod_comparable(
                a, acts, res['discipline'], window=window)
            return res
    return None


def _tod_comparable(act, acts, disc, window=BASELINE_WINDOW):
    """Blev baseline-passene lagt på nogenlunde samme tid af døgnet?

    Et eftermiddagsløb målt mod udelukkende morgenløb er ikke et rent
    sammenligningsgrundlag. Det gør ikke flaget forkert — det gør det
    forbeholdent, og forbeholdet skal med i teksten.

    Kigger over hele baseline-vinduet, ikke kun de seneste par dage: to pas
    er for tyndt til at afgøre hvad "normalt tidspunkt" er.
    """
    h = start_hour(act)
    if h is None:
        return None
    day = (act.get('start_date_local') or '')[:10]
    try:
        ref = date.fromisoformat(day)
    except ValueError:
        return None
    cut = ref - timedelta(days=window)

    others = []
    for a in acts or []:
        if a is act:
            continue
        d2, _ef = session_ef(a)
        if d2 != disc:
            continue
        try:
            d = date.fromisoformat((a.get('start_date_local') or '')[:10])
        except ValueError:
            continue
        if not (cut <= d < ref):
            continue
        oh = start_hour(a)
        if oh is not None:
            others.append(oh)
    if len(others) < MIN_BASELINE:
        return None
    return all(abs(oh - h) <= 3 for oh in others)


def _hhmm(hour):
    return f"kl. {hour:02d}" if hour is not None else None


def _dk(v, decimals=1):
    """Dansk decimalkomma. Teksten går direkte videre til Kennet."""
    return f"{v:.{decimals}f}".replace('.', ',')


def _dk_date(iso):
    """2026-08-25 -> 25/8. Coachen skriver ikke ISO-datoer."""
    try:
        y, m, d = iso.split('-')
        return f"{int(d)}/{int(m)}"
    except (ValueError, AttributeError):
        return iso


def format_note(flag):
    """Én dansk sætning til coach-prompten. None hvis der intet er at sige.

    Formuleret som observation med forbehold, ikke som dom. Coachen skal
    kunne sige "det her pas var dyrere end normalt, og her er hvorfor det
    måske ikke betyder noget" — begge halvdele i samme åndedrag.
    """
    if not flag or not flag.get('flagged'):
        return None

    disc = 'Løbeturen' if flag['discipline'] == RUN_DISC else 'Cykelpasset'
    pct = abs(flag['pct'])
    hr = flag.get('avg_hr')
    hr_s = f" (snitpuls {hr})" if hr else ""
    hard = flag['level'] == 'strong'

    s = (f"{disc} {_dk_date(flag['date'])}{hr_s} kostede {_dk(pct)} % mere puls pr. meter "
         f"end medianen af de seneste {flag['n_baseline']} sammenlignelige pas "
         f"(EF {_dk(flag['ef'], 3)} mod {_dk(flag['baseline'], 3)}).")

    caveats = []
    if flag.get('warm'):
        caveats.append(f"det var {_dk(flag['temp_c'])} °C")
    if flag.get('afternoon'):
        t = _hhmm(flag.get('start_hour'))
        caveats.append(f"passet startede {t}" if t else "passet lå om eftermiddagen")
    if flag.get('time_of_day_comparable') is False:
        caveats.append("baseline-passene lå på et andet tidspunkt af døgnet")

    if caveats:
        s += (" Forbehold, som IKKE er trukket fra tallet: "
              + ", ".join(caveats) + ".")
    s += (" Konkluder ikke overtræning ud fra ét pas — sig hvad passet kostede, "
          "og at det enten var varmen eller for højt tempo.")
    if hard:
        s = "VIGTIGT: " + s
    return s
