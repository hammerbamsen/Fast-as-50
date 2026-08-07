# -*- coding: utf-8 -*-
"""Tests for coach.py — distance-flag i coach-tekst og AI-prompt (rettet 7/8-2026).

build_distance_focus_line() bruges af generate_coach_speech() (hårdkodet tekst),
build_distance_prompt_line() af generate_ai_assessment() (AI-prompt-kontekst).
Begge er udtrukket som selvstændige funktioner så de kan testes uden en fuld
week_sessions-liste eller et Anthropic-API-kald.
"""
from datetime import date

from . import coach

TODAY_WEEKDAY = date.today().weekday()


# ── build_distance_focus_line (coach-tekst) ─────────────────────────────

def test_focus_line_flags_shortfall_with_real_numbers():
    session = {
        "label": "OW-svøm 2500m SAMMENHÆNGENDE (Christiansborg-generalprøve)",
        "planned_distance_m": 2500, "actual_distance_m": 1390,
    }
    line = coach.build_distance_focus_line(session)
    assert line is not None
    assert "1390 af 2500m" in line
    assert "56%" in line
    assert "under målet" in line


def test_focus_line_none_when_goal_met():
    session = {"label": "Svøm 2000m teknisk", "planned_distance_m": 2000, "actual_distance_m": 2100}
    assert coach.build_distance_focus_line(session) is None


def test_focus_line_none_without_distance_target():
    session = {"label": "Svøm let 30 min recovery", "planned_distance_m": None, "actual_distance_m": 1200}
    assert coach.build_distance_focus_line(session) is None


def test_focus_line_none_when_no_distance_data_reported():
    """Garmin/Intervals har ikke rapporteret distance -> intet flag, ikke en falsk alarm."""
    session = {"label": "OW-svøm 2500m", "planned_distance_m": 2500, "actual_distance_m": None}
    assert coach.build_distance_focus_line(session) is None


def test_focus_line_none_when_no_session():
    assert coach.build_distance_focus_line(None) is None


def test_focus_line_respects_custom_threshold():
    session = {"label": "Svøm 2000m", "planned_distance_m": 2000, "actual_distance_m": 1900}  # 95%
    assert coach.build_distance_focus_line(session, shortfall_threshold=0.80) is None
    assert coach.build_distance_focus_line(session, shortfall_threshold=0.98) is not None


# ── build_distance_prompt_line (AI-prompt) ──────────────────────────────

def test_prompt_line_includes_numbers_and_instruction():
    session = {"planned_distance_m": 2500, "actual_distance_m": 1390}
    line = coach.build_distance_prompt_line(session)
    assert "1390 af 2500" in line
    assert "56%" in line
    assert "EKSPLICIT" in line


def test_prompt_line_empty_without_distance_target():
    assert coach.build_distance_prompt_line({"planned_distance_m": None, "actual_distance_m": 1200}) == ""


def test_prompt_line_empty_when_no_distance_data_reported():
    assert coach.build_distance_prompt_line({"planned_distance_m": 2500, "actual_distance_m": None}) == ""


def test_prompt_line_empty_when_no_session():
    assert coach.build_distance_prompt_line(None) == ""


# ── generate_coach_speech — end-to-end tekst (samme scenarie som sagen) ─

def _base_speech_kwargs(today_session, week_sessions):
    return dict(
        week_num=10, weekday=TODAY_WEEKDAY, streak=3, af_this_week=2,
        today_session=today_session, block_type="BUILD", week_focus="Build-uge",
        ctl=55, tsb=-8, weight=71.5, sleep=7.2, compliance=85, tss_act=100,
        planned=120, remaining_sessions=[], week_sessions=week_sessions,
        days_completed=TODAY_WEEKDAY,
    )


def test_generate_coach_speech_mentions_distance_shortfall():
    today_session = {
        "today": True, "done": True, "disc": "openwater",
        "label": "OW-svøm 2500m SAMMENHÆNGENDE (Christiansborg-generalprøve)",
        "planned_distance_m": 2500, "actual_distance_m": 1390,
    }
    speech, _highlight = coach.generate_coach_speech(
        **_base_speech_kwargs(today_session, [today_session]))
    assert "1390 af 2500m" in speech
    assert "56%" in speech
    assert "under målet" in speech


def test_generate_coach_speech_silent_when_no_distance_target():
    today_session = {
        "today": True, "done": True, "disc": "bike", "label": "Cykel Z2 90 min",
        "planned_distance_m": None, "actual_distance_m": None,
    }
    speech, _highlight = coach.generate_coach_speech(
        **_base_speech_kwargs(today_session, [today_session]))
    assert "under målet" not in speech
