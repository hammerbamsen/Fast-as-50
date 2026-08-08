# -*- coding: utf-8 -*-
"""Tests for sessions.py — distance-bevidst completion (rettet 7/8-2026).

Rodårsag: en session med et eksplicit meter-mål (typisk svøm) kunne fremstå
'done' udelukkende ud fra TSS/tid, selvom den faktiske distance lå markant
under planen — fordi 1) distance slet ikke indgik i calc_completion, og
2) planned_tss/planned_mins reelt aldrig blev lagt på session-objektet i
get_planned_weeks(), så completion typisk faldt tilbage til "ingen data,
antag done". Sagen der udløste rettelsen: 7/8-2026, OW-svøm planlagt 2500m/
50 min/45 TSS, realiseret 1390m/33 min/33 TSS — coachen nævnte intet om
distancen, fordi den aldrig blev sammenlignet.
"""
from datetime import date

from . import sessions

TODAY_KEY = sessions.DAY_SHORT[date.today().weekday()]


# ── parse_planned_distance_m ────────────────────────────────────────────

def test_parse_distance_simple():
    assert sessions.parse_planned_distance_m("Svøm 2000m teknisk") == 2000


def test_parse_distance_with_surrounding_text():
    assert sessions.parse_planned_distance_m(
        "OW-svøm 2500m SAMMENHÆNGENDE (Christiansborg-generalprøve)") == 2500


def test_parse_distance_range_uses_upper_bound():
    assert sessions.parse_planned_distance_m("OW-svøm 800-1500m") == 1500


def test_parse_distance_ignores_minutes():
    assert sessions.parse_planned_distance_m("OW-svøm Open water 40 min") is None
    assert sessions.parse_planned_distance_m("Svøm let 30 min recovery") is None


def test_parse_distance_reads_km_but_ignores_hm():
    """Ændret 8/8-2026. Tidligere blev km bevidst ignoreret, fordi funktionen
    kun skulle dække svøm i meter. Konsekvensen var at løb og cykel ALDRIG fik
    et distance-mål, og coach-prompten citerede derfor plantallet fra label'en
    som udført distance — 28,2 km løbet blev refereret som '29 km'.
    Højdemeter (hm) skal fortsat IKKE opfattes som distance."""
    assert sessions.parse_planned_distance_m(
        "Løb Fornalutx – Far des Cap Gros loop, 21,28 km / 502 hm") == 21280
    assert sessions.parse_planned_distance_m("Cykel bjergpas 1200 hm") is None
    assert sessions.parse_planned_distance_m("Cykel bjergpas 1200hm") is None


def test_parse_distance_km_variants():
    assert sessions.parse_planned_distance_m("Lang løb Z2 29 km (155 min)") == 29000
    assert sessions.parse_planned_distance_m("Cykel Formentor 149km") == 149000
    assert sessions.parse_planned_distance_m("Løb 28-30 km marathon-ladder") == 30000


def test_parse_distance_km_takes_priority_over_minutes():
    """'155 min' må aldrig blive til et distance-mål, og km-grenen må ikke
    lade meter-grenen snuppe et tilfældigt 3-cifret tal i samme label."""
    assert sessions.parse_planned_distance_m("Lang løb Z2 32 km (170 min)") == 32000
    assert sessions.parse_planned_distance_m("Løb Z1 30 min let") is None


def test_compliance_prompt_line_shows_actual_distance():
    """Regressionsvagt for selve fejlen: prompt-linjen skal vise den FAKTISKE
    distance, ikke kun planens label."""
    line = sessions.format_compliance_for_prompt([{
        'day': 'Lør', 'label': 'Lang løb Z2 29 km', 'zone_flag': 'ok',
        'note': '66% i Z2 (pace) — on target',
        'moving_mins': 147, 'planned_mins': 155,
        'distance_m': 28227.0, 'planned_distance_m': 29000,
    }])
    assert '28,2/29,0 km' in line
    assert '147/155 min' in line


def test_parse_distance_no_match_returns_none():
    assert sessions.parse_planned_distance_m("Styrke A") is None
    assert sessions.parse_planned_distance_m("") is None
    assert sessions.parse_planned_distance_m(None) is None


# ── calc_completion — distance som ekstra dimension ─────────────────────

def test_completion_distance_shortfall_overrides_ok_time():
    """Dagens faktiske sag (7/8-2026): TSS/tid ser fint ud (73%/66%), men
    distancen (56%) er det svageste mål og skal afgøre status."""
    status, pct = sessions.calc_completion(
        actual_tss=33, planned_tss=45, actual_mins=33, planned_mins=50,
        actual_distance_m=1390, planned_distance_m=2500,
    )
    assert status == "partial"
    assert pct == 56


def test_completion_distance_met_stays_done():
    status, pct = sessions.calc_completion(
        actual_tss=45, planned_tss=45, actual_mins=50, planned_mins=50,
        actual_distance_m=2600, planned_distance_m=2500,
    )
    assert status == "done"


def test_completion_missing_distance_data_not_penalized():
    """Garmin/Intervals har ikke rapporteret distance for aktiviteten ->
    distance-kandidaten skal IGNORERES, ikke tælle som 0m (falsk 'minimal')."""
    status, pct = sessions.calc_completion(
        actual_tss=40, planned_tss=45, actual_mins=None, planned_mins=None,
        actual_distance_m=None, planned_distance_m=2500,
    )
    assert status == "done"  # 40/45 = 89% -- distance udelades pga. manglende data


def test_completion_no_distance_target_unchanged_behavior():
    """Ingen distance-mål i planen -> identisk med adfærden før rettelsen."""
    status, pct = sessions.calc_completion(
        actual_tss=35, planned_tss=70, actual_mins=None, planned_mins=None,
    )
    assert status == "partial"
    assert pct == 50


def test_completion_total_data_gap_still_assumes_done():
    assert sessions.calc_completion(None, None, None, None) == ("done", None)


# ── build_week_sessions — fuld pipeline med mock Intervals-data ─────────

def test_build_week_sessions_flags_todays_swim_shortfall():
    planned = [{
        "day": TODAY_KEY, "disc": "openwater",
        "label": "OW-svøm 2500m SAMMENHÆNGENDE (Christiansborg-generalprøve)",
        "done": False, "today": True,
        "planned_tss": 45, "planned_mins": 50, "planned_distance_m": 2500,
    }]
    done_map = {
        TODAY_KEY: [("openwater", "Gentofte Svømning i åbent vand", 33, 33,
                      None, None, None, None, "act123", 1390)]
    }
    result = sessions.build_week_sessions(done_map, planned)
    today = next(s for s in result if s.get("today"))
    assert today["completion"] == "partial"
    assert today["completion_pct"] == 56
    assert today["actual_distance_m"] == 1390
    assert today["planned_distance_m"] == 2500
    assert today["done"] is True  # partial tæller stadig som "forsøgt" (uændret semantik)


def test_build_week_sessions_no_distance_target_unaffected():
    """Regression: pas uden meter-mål i planen (fx cykel) skal opføre sig
    som før — ingen distance-felter, ren TSS/tid-vurdering."""
    planned = [{
        "day": TODAY_KEY, "disc": "bike", "label": "Cykel Z2 90 min",
        "done": False, "today": True,
        "planned_tss": None, "planned_mins": None, "planned_distance_m": None,
    }]
    done_map = {
        TODAY_KEY: [("bike", "Morgentur", 68, 88, None, None, None, None, "act456", None)]
    }
    result = sessions.build_week_sessions(done_map, planned)
    today = next(s for s in result if s.get("today"))
    assert today["completion"] == "done"
    assert today.get("actual_distance_m") is None
    assert today.get("planned_distance_m") is None
