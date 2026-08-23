"""Tests for aerobic.py — EF-beregning og filtre.

Fixtures er bygget på FAKTISKE tal fra Intervals 23/8-2026 (diagnosekørsel),
ikke opfundne. Det er meningen: filtrene skal testes mod de pas der rent
faktisk har givet problemer.
"""
from datetime import date

from .aerobic import (run_ef, bike_ef, build_points, trend, _hard_fraction,
                      _is_aerobic, _median)


def _run(**kw):
    """Fladt Gentofte-Z2-løb som udgangspunkt — 18/8-2026."""
    base = {
        'type': 'Run',
        'start_date_local': '2026-08-18T06:00:00',
        'moving_time': 131 * 60,
        'distance': 25760.0,
        'total_elevation_gain': 211.0,
        'gap': 3.286961,
        'average_speed': 3.269,
        'average_heartrate': 145,
        'icu_intensity': 87.0,
        'icu_hr_zone_times': [1200, 4000, 2660, 0, 0, 0, 0],
        'race': 0,
        'name': 'Gentofte - Lang løb Z2 26 km',
        'id': 'i1',
    }
    base.update(kw)
    return base


def _ride(**kw):
    """Hometrainer-pas 22/8-2026."""
    base = {
        'type': 'VirtualRide',
        'start_date_local': '2026-08-22T06:00:00',
        'moving_time': 47 * 60,
        'icu_efficiency_factor': 1.48,
        'icu_intensity': 66.5,
        'icu_hr_zone_times': [2836, 0, 0, 0, 0, 0, 0],
        'trainer': True,
        'race': 0,
        'name': 'Hometrainer Z2',
        'id': 'i2',
    }
    base.update(kw)
    return base


# --- Løbe-EF ---------------------------------------------------------------

def test_run_ef_beregnes_fra_gap_ikke_average_speed():
    """GAP, ikke average_speed. Ellers straffes bakkeløb som formtab."""
    ef = run_ef(_run())
    assert ef == round(3.286961 * 60 / 145, 3) == 1.36


def test_bergen_bakkeloeb_ville_se_helt_forskelligt_ud_med_average_speed():
    """Bergen 23/8: average_speed 2,372 vs gap 3,039 — 28 % forskel.

    Passet falder ud på hm/km-filteret (52,7), men pointen står: forskellen
    mellem de to felter er hele forskellen på et brugbart og et misvisende tal.
    """
    bergen = _run(distance=6957.21, total_elevation_gain=366.35,
                  gap=3.0393076, average_speed=2.372,
                  average_heartrate=134, moving_time=48 * 60)
    assert run_ef(bergen) is None          # for stejlt
    naiv = round(2.372 * 60 / 134, 3)
    korrekt = round(3.0393076 * 60 / 134, 3)
    assert korrekt - naiv > 0.25           # naiv ville vise ~20 % formtab


def test_stejlt_loeb_frasorteres():
    assert run_ef(_run(distance=4720.0, total_elevation_gain=120.0,
                       moving_time=40 * 60)) is None


def test_moderat_kuperet_loeb_beholdes():
    """8 hm/km er normalt for Gentofte — må ikke ryge ud."""
    assert run_ef(_run(distance=21700.0, total_elevation_gain=171.0)) is not None


def test_kort_pas_frasorteres():
    assert run_ef(_run(moving_time=24 * 60)) is None


def test_vo2_pas_frasorteres_paa_zonetider():
    """VO2-pas har samme IF som lange Z2-løb — kun zonetiderne skiller dem."""
    vo2 = _run(icu_hr_zone_times=[600, 900, 700, 500, 300, 0, 0],
               icu_intensity=88.0, name='Løb VO2 4×5 min Z4-Z5')
    assert vo2['icu_intensity'] > _run()['icu_intensity']  # IF duer ikke som si
    assert run_ef(vo2) is None


def test_loeb_uden_puls_frasorteres():
    assert run_ef(_run(average_heartrate=None)) is None


def test_race_frasorteres():
    assert run_ef(_run(race=1)) is None


def test_intervals_eget_ef_er_tomt_paa_loeb():
    """Dokumenterer hvorfor vi regner selv: feltet findes, men er None."""
    r = _run(icu_efficiency_factor=None)
    assert run_ef(r) is not None


# --- Cykel-EF --------------------------------------------------------------

def test_bike_ef_paa_hometrainer():
    assert bike_ef(_ride()) == 1.48


def test_udendoers_cykel_frasorteres():
    """Mallorca-bjergtur: EF 1,07 mod 1,48 indendørs — terræn, ikke form."""
    ude = _ride(type='Ride', trainer=None, icu_efficiency_factor=1.0737705,
                moving_time=215 * 60, icu_intensity=47.1)
    assert bike_ef(ude) is None


def test_cykel_uden_power_frasorteres():
    assert bike_ef(_ride(icu_efficiency_factor=None)) is None


def test_kort_cykelpas_frasorteres():
    assert bike_ef(_ride(moving_time=20 * 60)) is None


# --- Hjælpere --------------------------------------------------------------

def test_hard_fraction():
    assert _hard_fraction({'icu_hr_zone_times': [50, 50, 0, 0, 0, 0, 0]}) == 0.0
    assert _hard_fraction({'icu_hr_zone_times': [0, 0, 50, 50, 0, 0, 0]}) == 0.5
    assert _hard_fraction({}) is None


def test_is_aerobic_falder_tilbage_paa_if_uden_zonetider():
    assert _is_aerobic({'icu_intensity': 70}) is True
    assert _is_aerobic({'icu_intensity': 95}) is False
    assert _is_aerobic({}) is False


def test_median():
    assert _median([1, 2, 3]) == 2
    assert _median([1, 2, 3, 4]) == 2.5
    assert _median([]) is None


# --- Historik og trend -----------------------------------------------------

def test_build_points_sorterer_og_adskiller_discipliner():
    acts = [_ride(), _run(start_date_local='2026-08-01T06:00:00', id='i3'), _run()]
    pts = build_points(acts)
    assert len(pts['run']) == 2 and len(pts['bike']) == 1
    assert pts['run'][0]['date'] == '2026-08-01'
    assert pts['run'][1]['date'] == '2026-08-18'


def test_build_points_springer_pas_uden_dato_over():
    assert build_points([_run(start_date_local=None)])['run'] == []


def test_trend_sammenligner_to_42_dages_vinduer():
    pts = ([{'date': '2026-06-01', 'v': 1.20}] * 1 +
           [{'date': '2026-06-05', 'v': 1.30}, {'date': '2026-06-10', 'v': 1.25}] +
           [{'date': '2026-08-01', 'v': 1.35}, {'date': '2026-08-10', 'v': 1.40},
            {'date': '2026-08-18', 'v': 1.36}])
    t = trend(pts, today=date(2026, 8, 23))
    assert t['current'] == 1.36
    assert t['previous'] == 1.25
    assert t['pct'] == round((1.36 - 1.25) / 1.25 * 100, 1)
    assert t['thin'] is False


def test_trend_melder_tyndt_grundlag_frem_for_at_gaette():
    t = trend([{'date': '2026-08-20', 'v': 1.4}], today=date(2026, 8, 23))
    assert t['current'] is None
    assert t['thin'] is True
    assert t['n'] == 1


def test_trend_uden_pct_naar_forrige_vindue_er_tomt():
    pts = [{'date': '2026-08-01', 'v': 1.3}, {'date': '2026-08-10', 'v': 1.35},
           {'date': '2026-08-18', 'v': 1.36}]
    t = trend(pts, today=date(2026, 8, 23))
    assert t['current'] == 1.35
    assert t['previous'] is None
    assert t['pct'] is None


def test_trend_taaler_defekte_datoer():
    pts = [{'date': 'ikke-en-dato', 'v': 1.3}, {'date': '2026-08-01', 'v': 1.3},
           {'date': '2026-08-10', 'v': 1.35}, {'date': '2026-08-18', 'v': 1.36}]
    assert trend(pts, today=date(2026, 8, 23))['current'] == 1.35
