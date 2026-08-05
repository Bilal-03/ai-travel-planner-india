"""Prompt-first clarification contract coverage."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

from app.models.planner import PlannerAnswer, PlannerClarificationRequest
from app.services import prompt_planner


def test_ready_gemini_response_becomes_a_single_trip_request(monkeypatch):
    start = date.today() + timedelta(days=14)

    async def fake_gemini(_prompt, system=None):
        return {
            "status": "ready",
            "brief": {
                "origin": "Delhi",
                "destination": "Jaipur",
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=2)).isoformat(),
                "budget": 30_000,
                "members": 3,
                "transport_mode": "train",
                "planning_notes": "heritage places and local food",
                "preferences": {"experiences": ["heritage & culture"], "pace": "balanced"},
            },
            "questions": [],
        }

    monkeypatch.setattr(prompt_planner, "_call_gemini", fake_gemini)
    result = asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(prompt="Plan a heritage trip")))

    assert result.status == "ready"
    assert result.trip_request is not None
    assert result.trip_request.members == 3
    assert result.trip_request.transport_mode.value == "train"
    assert result.trip_request.preferences.pace.value == "balanced"


def test_missing_details_return_numbered_questions_without_old_form_fields(monkeypatch):
    async def unavailable(_prompt, system=None):
        return None

    monkeypatch.setattr(prompt_planner, "_call_gemini", unavailable)
    result = asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(prompt="Plan a trip to Jaipur")))

    assert result.status == "questions"
    assert result.trip_request is None
    assert result.questions
    assert all(question.options or question.allow_custom for question in result.questions)
    assert set(result.brief.model_dump()) == {
        "origin", "destination", "start_date", "end_date", "budget", "members",
        "transport_mode", "planning_notes", "preferences",
    }


def test_complete_fallback_prompt_generates_without_optional_transport(monkeypatch):
    async def unavailable(_prompt, system=None):
        return None

    monkeypatch.setattr(prompt_planner, "_call_gemini", unavailable)
    result = asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(
        prompt="Plan a relaxed heritage trip for 3 days from Delhi to Jaipur for 2 people under ₹30,000",
    )))

    assert result.status == "ready"
    assert result.questions == []
    assert result.trip_request is not None
    assert result.trip_request.members == 2


def test_fallback_parser_separates_natural_date_range_from_destination():
    brief = prompt_planner._heuristic_brief(
        "Plan 5 days from Delhi to Manali, 14 Aug 2026 to 18 Aug 2026, for 2 members, total budget ₹30,000.",
        [],
    )

    assert brief.origin == "delhi"
    assert brief.destination == "manali"
    assert brief.start_date == date(2026, 8, 14)
    assert brief.end_date == date(2026, 8, 18)
    assert brief.members == 2
    assert brief.budget == 30_000


def test_model_brief_is_repaired_from_explicit_prompt_facts(monkeypatch):
    async def fake_gemini(_prompt, system=None):
        return {
            "status": "ready",
            "brief": {
                "origin": "delhi",
                "destination": "manali, 14 aug 2026 to 18 aug 2026",
                "start_date": "2026-08-19",
                "end_date": "2026-08-23",
                "budget": 30_000,
                "members": 2,
                "preferences": {"experiences": ["mountains & outdoors"], "pace": "balanced"},
            },
            "questions": [],
        }

    monkeypatch.setattr(prompt_planner, "_call_gemini", fake_gemini)
    result = asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(
        prompt="Plan 5 days from Delhi to Manali, 14 Aug 2026 to 18 Aug 2026, for 2 members, total budget ₹30,000.",
    )))

    assert result.brief.destination == "manali"
    assert result.brief.start_date == date(2026, 8, 14)
    assert result.brief.end_date == date(2026, 8, 18)


def test_answers_are_sent_back_as_context(monkeypatch):
    captured: list[str] = []
    start = date.today() + timedelta(days=10)

    async def fake_gemini(prompt, system=None):
        captured.append(prompt)
        return {
            "status": "ready",
            "brief": {
                "origin": "Delhi",
                "destination": "Goa",
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=1)).isoformat(),
                "budget": 20_000,
                "members": 2,
                "planning_notes": "beach and food",
                "preferences": {"experiences": ["beaches & backwaters"], "pace": "relaxed"},
            },
            "questions": [],
        }

    monkeypatch.setattr(prompt_planner, "_call_gemini", fake_gemini)
    asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(
        prompt="Plan a Goa trip",
        answers=[PlannerAnswer(question_id="members", option_id="two", answer="2 members")],
    )))

    assert "2 members" in captured[0]


def test_complete_prompt_uses_the_two_step_india_preference_ladder(monkeypatch):
    async def unavailable(_prompt, system=None):
        return None

    monkeypatch.setattr(prompt_planner, "_call_gemini", unavailable)
    prompt = "Plan 3 days from Delhi to Jaipur for 2 people under ₹30,000"

    first = asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(prompt=prompt)))
    assert first.status == "questions"
    assert first.questions[0].id == "experiences"

    second = asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(
        prompt=prompt,
        answers=[PlannerAnswer(question_id="experiences", option_id="heritage", answer="Heritage & culture")],
    )))
    assert second.status == "questions"
    assert second.questions[0].id == "pace"

    third = asyncio.run(prompt_planner.clarify_planner(PlannerClarificationRequest(
        prompt=prompt,
        answers=[
            PlannerAnswer(question_id="experiences", option_id="heritage", answer="Heritage & culture"),
            PlannerAnswer(question_id="pace", option_id="relaxed", answer="Relaxed"),
        ],
    )))
    assert third.status == "ready"
    assert third.trip_request is not None
    assert third.trip_request.preferences.experiences == ["Heritage & culture"]
    assert third.trip_request.preferences.pace.value == "relaxed"
