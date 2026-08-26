# -*- coding: utf-8 -*-
"""Tests for decoupling.py — per-pas EF-flag.

Fixtures bygger på FAKTISKE tal fra Intervals august 2026, ikke opfundne:

  18/8  Lang Z2 26 km   131 min  gap 3,287  puls 145  -> EF 1,360
  23/8  Bergen 7 km      49 min  gap 3,040  puls 134  -> EF 1,361
  25/8  "Z2 18 km"       94 min  gap 3,200  puls 151  -> EF 1,272

Det er hele pointen med sagen: 25/8 skal flages, og de to andre må ikke.
Ville reglen også have råbt op ad 18/8 eller Bergen, var den ubrugelig.
"""
from datetime import date

import pytest

from .decoupling import (evaluate, latest, baseline_ef, format_note,
                         session_temp, start_hour, session_ef, _level,
                         NOTICE_PCT, STRONG_PCT)


# ── fixtures ────────────────────────────────────────────────────────────────

def _run(**kw):
    """Fladt Gentofte-Z2-løb, morgen. Default = 18/8-2026 (baseline-passet)."""
    base = {
        'type': 'Run',
        'start_date_local': '2026-08-18T07:03:41',
        'moving_time': 131 * 60,
        'distance': 25760.0,
        'total_elevation_gain': 211.0,
        'gap': 3.286961,
        'average_heartrate': 145,
        'icu_intensity': 87.0,
        'icu_hr_zone_times': [1200, 4000, 2660, 0, 0, 0, 0],
        'race': 0,
        'name': 'Gentofte - Lang løb Z2 26 km',
        'id': 'i18',
    }
    base.update(kw)
    return base


def _run_2508(**kw):
    """25/8: eftermiddag, langsommere tempo, højere puls. Sagens kerne."""
    d = dict(start_date_local='2026-08-25T14:56:36',
             moving_time=94 * 60, distance=17830.0,
             total_elevation_gain=95.0, gap=3.200,
             average_heartrate=151, average_temp=24.0,
             name='Gentofte - Løb Z2 18 km', id='i25')
    d.update(kw)
    return _run(**d)


def _run_bergen(**kw):
    """23/8 Bergen: langsomt på uret, men GAP retter for stigningen."""
    d = dict(start_date_local='2026-08-23T06:35:26',
             moving_time=49 * 60, distance=6960.0,
             total_elevation_gain=90.0, gap=3.040,
             average_heartrate=134, name='Bergen Løb', id='i23')
    d.update(kw)
    return _run(**d)


def _pts(*vals, start='2026-08-05'):
    """EF-punkter med én dags mellemrum fra `start`."""
    d0 = date.fromisoformat(start)
    from datetime import timedelta
    return [{'date': str(d0 + timedelta(days=i)), 'v': v}
            for i, v in enumerate(vals)]


BASE_RUN = {'run': _pts(1.358, 1.362, 1.360, 1.361), 'bike': []}


# ── kernen: hvad skal og hvad skal ikke flages ──────────────────────────────

def test_2508_flages():
    r = evaluate(_run_2508(), BASE_RUN)
    assert r is not None
    assert r['flagged'] is True
    assert r['level'] == 'notice'
    assert r['pct'] == pytest.approx(-6.5, abs=0.3)
    assert r['avg_hr'] == 151


def test_1808_flages_ikke():
    """Baseline-passet selv må aldrig flage — ellers er målestokken skæv."""
    r = evaluate(_run(), BASE_RUN)
    assert r is not None and r['flagged'] is False and r['level'] == 'ok'


def test_bergen_flages_ikke_selvom_tempoet_er_langsomt():
    """2,37 m/s på uret, men GAP 3,04. Uden GAP ville bakkeløb ligne formtab."""
    r = evaluate(_run_bergen(), BASE_RUN)
    assert r is not None and r['flagged'] is False


def test_stort_fald_giver_strong():
    r = evaluate(_run_2508(gap=3.00, average_heartrate=155), BASE_RUN)
    assert r['level'] == 'strong'
    assert r['pct'] <= STRONG_PCT


def test_ef_stigning_er_ikke_et_flag():
    r = evaluate(_run(average_heartrate=132), BASE_RUN)
    assert r['pct'] > 0 and r['flagged'] is False


# ── filtre arvet fra aerobic.py: tavshed frem for gæt ───────────────────────

def test_for_kort_pas_giver_intet():
    """Shakeout 20/8 var 24 min — under MIN_RUN_SECS, ikke sammenligneligt."""
    assert evaluate(_run(moving_time=24 * 60, distance=4600.0), BASE_RUN) is None


def test_intervalpas_giver_intet():
    hard = _run(icu_hr_zone_times=[600, 1200, 1500, 2000, 800, 0, 0])
    assert evaluate(hard, BASE_RUN) is None


def test_manglende_puls_giver_intet():
    assert evaluate(_run(average_heartrate=None), BASE_RUN) is None


def test_for_stejlt_giver_intet():
    assert evaluate(_run(distance=6000.0, total_elevation_gain=400.0), BASE_RUN) is None


def test_tynd_baseline_giver_intet():
    """To punkter er ikke en median. Så siger modulet ingenting."""
    assert evaluate(_run_2508(), {'run': _pts(1.36, 1.36), 'bike': []}) is None


def test_cykel_baseline_bruges_ikke_paa_loeb():
    thin = {'run': [], 'bike': _pts(1.50, 1.52, 1.51)}
    assert evaluate(_run_2508(), thin) is None


# ── baseline_ef ─────────────────────────────────────────────────────────────

def test_baseline_ekskluderer_passet_selv():
    """Strengt 'før': et dårligt pas må ikke trække sin egen målestok ned."""
    pts = _pts(1.36, 1.36, 1.36) + [{'date': '2026-08-25', 'v': 0.9}]
    base, n = baseline_ef(pts, '2026-08-25')
    assert base == 1.36 and n == 3


def test_baseline_ignorerer_gamle_punkter():
    old = [{'date': '2026-01-01', 'v': 1.2}] * 5
    base, n = baseline_ef(old + _pts(1.36, 1.36, 1.36), '2026-08-25')
    assert n == 3 and base == 1.36


def test_baseline_taaler_skrald():
    pts = _pts(1.36, 1.36, 1.36) + [{'date': 'ikke-en-dato', 'v': 9},
                                    {'date': '2026-08-20'},
                                    {'date': '2026-08-21', 'v': None}]
    base, n = baseline_ef(pts, '2026-08-25')
    assert base == 1.36 and n == 3


# ── kontekst: varme og tidspunkt vedhæftes, men trækkes ikke fra ────────────

def test_varme_og_eftermiddag_registreres():
    r = evaluate(_run_2508(), BASE_RUN)
    assert r['temp_c'] == 24.0 and r['warm'] is True
    assert r['start_hour'] == 14 and r['afternoon'] is True


def test_varme_aendrer_ikke_tallet():
    """Afgørende: konteksten må aldrig korrigere EF — det ville være opdigtet præcision."""
    varm = evaluate(_run_2508(), BASE_RUN)
    kold = evaluate(_run_2508(average_temp=8.0), BASE_RUN)
    assert varm['pct'] == kold['pct'] == varm['pct']
    assert kold['warm'] is False


def test_morgenpas_er_ikke_eftermiddag():
    r = evaluate(_run(), BASE_RUN)
    assert r['afternoon'] is False


@pytest.mark.parametrize('felt', ['average_temp', 'icu_weather_temp',
                                  'weather_temp', 'temperature'])
def test_temperatur_laeses_fra_alle_kendte_felter(felt):
    assert session_temp({felt: 21.4}) == 21.4


def test_ukendt_temperatur_er_ikke_koldt():
    assert session_temp({}) is None
    assert evaluate(_run_2508(average_temp=None), BASE_RUN)['warm'] is False


def test_start_hour_taaler_skrald():
    assert start_hour({'start_date_local': 'xx'}) is None
    assert start_hour({}) is None


# ── latest() ────────────────────────────────────────────────────────────────

def test_latest_vaelger_nyeste_kvalificerede_pas():
    acts = [_run(), _run_bergen(), _run_2508()]
    r = latest(acts, BASE_RUN, today=date(2026, 8, 26))
    assert r['date'] == '2026-08-25' and r['flagged'] is True


def test_latest_springer_ikke_kvalificerede_over():
    """Styrketræning i går må ikke gøre coachen tavs om løbeturen."""
    styrke = {'type': 'WeightTraining', 'start_date_local': '2026-08-26T07:31:00',
              'moving_time': 20 * 60, 'average_heartrate': 91}
    r = latest([styrke, _run_2508()], BASE_RUN, today=date(2026, 8, 26))
    assert r is not None and r['date'] == '2026-08-25'


def test_latest_er_tavs_uden_nyt_pas():
    """Ingen nyheder er ikke en fejl — så siger coachen ingenting."""
    assert latest([_run()], BASE_RUN, today=date(2026, 9, 20)) is None
    assert latest([], BASE_RUN, today=date(2026, 8, 26)) is None
    assert latest(None, BASE_RUN, today=date(2026, 8, 26)) is None


def test_latest_ser_ikke_ind_i_fremtiden():
    fremtid = _run_2508(start_date_local='2026-09-01T14:00:00')
    assert latest([fremtid], BASE_RUN, today=date(2026, 8, 26)) is None


def test_eftermiddagspas_mod_morgenbaseline_markeres_uskarpt():
    morgener = [_run(start_date_local=f'2026-08-{d}T07:00:00', id=f'm{d}')
                for d in (10, 12, 14, 16)]
    r = latest(morgener + [_run_2508()], BASE_RUN, today=date(2026, 8, 26))
    assert r['time_of_day_comparable'] is False


def test_samme_tidspunkt_er_sammenligneligt():
    morgener = [_run(start_date_local=f'2026-08-{d}T07:00:00', id=f'm{d}')
                for d in (10, 12, 14, 16)]
    mål = _run(start_date_local='2026-08-25T06:40:00', average_heartrate=151, id='x')
    r = latest(morgener + [mål], BASE_RUN, today=date(2026, 8, 26))
    assert r['time_of_day_comparable'] is True


# ── format_note ─────────────────────────────────────────────────────────────

def test_note_naevner_tal_forbehold_og_forbud_mod_overtraeningsdom():
    note = format_note(latest([_run_2508()], BASE_RUN, today=date(2026, 8, 26)))
    assert '151' in note and '25' in note
    assert '24' in note and 'kl. 14' in note
    assert 'IKKE er trukket fra' in note
    assert 'overtræning' in note.lower()


def test_note_er_tom_naar_alt_er_fint():
    assert format_note(evaluate(_run(), BASE_RUN)) is None
    assert format_note(None) is None
    assert format_note({}) is None


def test_strong_markeres_som_vigtigt():
    note = format_note(evaluate(_run_2508(gap=3.00, average_heartrate=155), BASE_RUN))
    assert note.startswith('VIGTIGT:')


def test_note_uden_forbehold_naar_der_ingen_er():
    kold = evaluate(_run_2508(start_date_local='2026-08-25T06:30:00',
                              average_temp=9.0), BASE_RUN)
    assert 'IKKE er trukket fra' not in format_note(kold)


# ── _level ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize('pct,forventet', [
    (2.0, 'ok'), (0.0, 'ok'), (-4.9, 'ok'),
    (NOTICE_PCT, 'notice'), (-6.5, 'notice'), (-7.9, 'notice'),
    (STRONG_PCT, 'strong'), (-15.0, 'strong'), (None, 'ok'),
])
def test_level_graenser(pct, forventet):
    assert _level(pct) == forventet


def test_session_ef_paa_ukendt_type():
    assert session_ef({'type': 'Swim', 'moving_time': 3600}) == (None, None)
