"""Tests for søvn- og AF DAGE-KPI'erne i update_kpi.py (3/9-2026).

Søvn: værdi = sidste nat, sub = ægte 7d-snit fra sleepHistory, farve på snittet.
AF DAGE: værdi = AF-dage denne uge, sub = mål + 4-ugers snit + streak-hale.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import update_kpi as U  # noqa: E402


def _hist(vals):
    return [{'date': f'2026-09-{i+1:02d}', 'v': v, 'real': True} for i, v in enumerate(vals)]


def test_sleep_sidste_nat_og_7d_snit():
    last, avg7, sub, color = U.sleep_kpi(_hist([6.0, 6.0, 6.0, 8.0, 8.0, 8.0, 7.0, 7.0, 7.5, 7.6]))
    assert last == 7.6
    assert avg7 == round((8.0 + 8.0 + 8.0 + 7.0 + 7.0 + 7.5 + 7.6) / 7, 1)
    assert sub.startswith('Snit 7d ') and 'mål 7t' in sub
    assert color == '#27AE60'


def test_sleep_ignorerer_tomme_punkter():
    hist = _hist([7.0, 7.0]) + [{'date': '2026-09-03', 'v': None, 'real': False}]
    last, avg7, _, _ = U.sleep_kpi(hist)
    assert last == 7.0 and avg7 == 7.0


def test_sleep_farve_orange_og_roed():
    assert U.sleep_kpi(_hist([6.7] * 7))[3] == '#E67E22'
    assert U.sleep_kpi(_hist([6.2] * 7))[3] == '#C0392B'


def test_sleep_uden_historik_falder_tilbage():
    last, avg7, sub, color = U.sleep_kpi(None, fallback_avg=7.4)
    assert last == 7.4 and avg7 == 7.4 and color == '#27AE60'
    assert U.sleep_kpi([], fallback_avg=None)[3] == '#7A6A58'


def test_af_kpi_4_ugers_snit_kun_afsluttede_uger():
    hist = [{'week': 1, 'done': 7, 'total': 7}, {'week': 2, 'done': 5, 'total': 7},
            {'week': 3, 'done': 6, 'total': 7}, {'week': 4, 'done': 6, 'total': 7},
            {'week': 5, 'done': 5, 'total': 7}, {'week': 6, 'done': 2, 'total': 4}]
    sub, color = U.af_kpi(2, 3, hist, 6)
    assert sub == 'af 6 denne uge · snit 4 uger 5,5 · streak 3'
    assert color == '#59182A'


def test_af_kpi_uden_streak_og_maal_naaet():
    sub, color = U.af_kpi(6, 0, [{'week': 1, 'done': 3, 'total': 3}], 6)
    assert sub == 'af 6 denne uge · snit 4 uger 3,0'
    assert color == '#27AE60'
