"""Tests for 7-dages fallback på vægt/fedtprocent.

Baggrund: nattekørslen (00:0x) rammer før Garmin har synket dagens vejning.
Før fallbacken fik coachen weight=None og skrev "ingen aktuel vejning denne
uge" — selvom der lå reelle målinger fra de foregående dage.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.coach import last_real_within, dk_day, generate_coach_speech

TODAY = date(2026, 8, 6)


def _row(d, v, real=True):
    return {'date': str(d), 'v': v, 'real': real}


# ── last_real_within ─────────────────────────────────────────────────────────

def test_maaling_i_dag_returneres_med_dagens_dato():
    rows = [_row(TODAY - timedelta(days=1), 72.1), _row(TODAY, 72.2)]
    assert last_real_within(rows, today=TODAY) == (72.2, '2026-08-06')


def test_maaling_2_dage_gammel_falder_tilbage():
    rows = [_row(TODAY - timedelta(days=5), 72.9), _row(TODAY - timedelta(days=2), 72.1)]
    assert last_real_within(rows, today=TODAY) == (72.1, '2026-08-04')


def test_maaling_10_dage_gammel_afvises():
    rows = [_row(TODAY - timedelta(days=10), 73.4)]
    assert last_real_within(rows, today=TODAY) == (None, None)


def test_praecis_7_dage_er_indenfor_vinduet():
    rows = [_row(TODAY - timedelta(days=7), 73.0)]
    assert last_real_within(rows, today=TODAY) == (73.0, '2026-07-30')


def test_8_dage_er_udenfor_vinduet():
    rows = [_row(TODAY - timedelta(days=8), 73.0)]
    assert last_real_within(rows, today=TODAY) == (None, None)


def test_ingen_maalinger_giver_none():
    assert last_real_within([], today=TODAY) == (None, None)
    assert last_real_within(None, today=TODAY) == (None, None)


def test_none_huller_i_historikken_springes_over():
    rows = [_row(TODAY - timedelta(days=3), 72.6), None, {'date': '2026-08-05', 'v': None}]
    assert last_real_within(rows, today=TODAY) == (72.6, '2026-08-03')


def test_fremskrevet_maaling_real_false_ignoreres():
    rows = [_row(TODAY - timedelta(days=2), 72.1), _row(TODAY, 71.5, real=False)]
    assert last_real_within(rows, today=TODAY) == (72.1, '2026-08-04')


def test_ugyldig_dato_crasher_ikke():
    rows = [_row(TODAY - timedelta(days=1), 72.1), {'date': 'ikke-en-dato', 'v': 70.0}]
    assert last_real_within(rows, today=TODAY) == (72.1, '2026-08-05')


# ── dk_day ───────────────────────────────────────────────────────────────────

def test_dk_day_formaterer_dansk():
    assert dk_day('2026-08-05') == '5/8'
    assert dk_day('2026-12-24') == '24/12'


def test_dk_day_taaler_none_og_vroevl():
    assert dk_day(None) is None
    assert dk_day('') is None
    assert dk_day('vroevl') is None


# ── coach speech: datoen skal med når målingen ikke er fra i dag ─────────────

def _speech(weight, weight_date):
    text, _ = generate_coach_speech(
        10, 3, 2, 3, None, 'BUILD', 'Testfokus',
        ctl=51.7, tsb=-9.8, weight=weight, sleep=7.3,
        week_sessions=[], weight_goal=70, weight_date=weight_date,
    )
    return text


def test_speech_uden_dato_naevner_ikke_maalt():
    assert 'målt' not in _speech(72.2, None)


def test_speech_med_dato_naevner_datoen():
    assert '(målt 5/8)' in _speech(72.1, '2026-08-05')
