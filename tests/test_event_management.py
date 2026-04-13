"""Tests for event management tools — focusing on auto-translate integration."""

import json
from unittest.mock import MagicMock

import pytest
from httpx import Response

from intervals_icu_mcp.tools.event_management import (
    _get_sport_type,
    bulk_create_events,
    create_event,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ATHLETE_ID = "i123456"
EVENTS_URL = f"/athlete/{ATHLETE_ID}/events"
BULK_EVENTS_URL = f"/athlete/{ATHLETE_ID}/events/bulk"


def _make_event_response(
    event_id: int = 1001,
    name: str = "Test Workout",
    category: str = "WORKOUT",
    event_type: str = "Run",
    description: str | None = None,
    moving_time: int | None = None,
) -> dict:
    """Build a minimal Event API response dict."""
    payload: dict = {
        "id": event_id,
        "start_date_local": "2026-04-10T00:00:00",
        "name": name,
        "category": category,
        "type": event_type,
    }
    if description is not None:
        payload["description"] = description
    if moving_time is not None:
        payload["moving_time"] = moving_time
    return payload


def _make_ctx(mock_config):
    ctx = MagicMock()
    ctx.get_state.return_value = mock_config
    return ctx


# ---------------------------------------------------------------------------
# Unit: _get_sport_type helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event_type,expected",
    [
        ("Run", "Run"),
        ("run", "Run"),
        ("Trail Run", "Run"),
        ("Ride", "Ride"),
        ("VirtualRide", "Ride"),
        ("Cycling", "Ride"),
        ("Swim", "Swim"),
        ("OpenWaterSwim", "Swim"),
        (None, "Run"),
        ("", "Run"),
        ("Walk", "Run"),  # unknown → default Run
    ],
)
def test_get_sport_type(event_type, expected):
    assert _get_sport_type(event_type) == expected


# ---------------------------------------------------------------------------
# create_event — auto_translate=True (default)
# ---------------------------------------------------------------------------


class TestCreateEventAutoTranslate:
    """create_event with auto_translate=True (default)."""

    async def test_translates_finalsurge_description(self, mock_config, respx_mock):
        """A structured FinalSurge description is translated before being sent to the API."""
        finalsurge_desc = "Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )"
        duration = 2700  # 45 minutes

        # The API receives whatever description was POSTed; echo it back
        def _echo_handler(request):
            body = json.loads(request.content)
            return Response(
                200,
                json=_make_event_response(
                    description=body.get("description"),
                    moving_time=body.get("moving_time"),
                ),
            )

        respx_mock.post(EVENTS_URL).mock(side_effect=_echo_handler)

        result = await create_event(
            start_date="2026-04-10",
            name="Strides Run",
            category="WORKOUT",
            description=finalsurge_desc,
            event_type="Run",
            duration_seconds=duration,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        assert "data" in response
        # Description in the response should be the translated ICU format
        translated_desc = response["data"]["description"]
        assert "7x" in translated_desc, f"Expected 7x repeat block, got:\n{translated_desc}"
        assert "- 17s z5 pace" in translated_desc
        # Metadata must confirm translation happened
        assert response["metadata"]["description_translated"] is True
        assert "original_description" in response["metadata"]
        assert response["metadata"]["original_description"] == finalsurge_desc

    async def test_inline_repeat_pattern_translated(self, mock_config, respx_mock):
        """The new inline 'N x work and recovery' pattern is translated."""
        desc = "8 x 4:00mins @MP->HMP and 2:00mins easy"
        duration = 4800  # 1h20m

        def _echo_handler(request):
            body = json.loads(request.content)
            return Response(200, json=_make_event_response(description=body.get("description")))

        respx_mock.post(EVENTS_URL).mock(side_effect=_echo_handler)

        result = await create_event(
            start_date="2026-04-10",
            name="MP Intervals",
            category="WORKOUT",
            description=desc,
            event_type="Run",
            duration_seconds=duration,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        translated = response["data"]["description"]
        assert "8x" in translated
        assert "- 4m z4 pace" in translated
        assert response["metadata"]["description_translated"] is True

    async def test_no_translation_when_description_unchanged(self, mock_config, respx_mock):
        """When the translator produces the same text as the input, description_translated=False.

        A single-step ICU description like '- 30m z2 pace' contains no repeat pattern,
        so _build_simple re-produces the same string and the flag stays False.
        """
        # "- 30m z2 pace" → _identify_intensity finds "z2", _seconds_to_icu(1800)="30m"
        # → translate_workout returns "- 30m z2 pace" == original → no change
        already_icu = "- 30m z2 pace"

        respx_mock.post(EVENTS_URL).mock(
            return_value=Response(200, json=_make_event_response(description=already_icu))
        )

        result = await create_event(
            start_date="2026-04-10",
            name="Easy Run",
            category="WORKOUT",
            description=already_icu,
            event_type="Run",
            duration_seconds=1800,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        assert response["metadata"].get("description_translated") is False

    async def test_no_translation_without_duration(self, mock_config, respx_mock):
        """No translation is attempted when duration_seconds is absent."""
        desc = "6-8x( 15-20s @ Stride / Full recovery )"

        respx_mock.post(EVENTS_URL).mock(
            return_value=Response(200, json=_make_event_response(description=desc))
        )

        result = await create_event(
            start_date="2026-04-10",
            name="Strides",
            category="WORKOUT",
            description=desc,
            event_type="Run",
            duration_seconds=None,  # no duration → no translation
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        # No translation metadata should be present at all
        assert "description_translated" not in response["metadata"]

    async def test_no_translation_for_non_workout_category(self, mock_config, respx_mock):
        """Non-WORKOUT categories (NOTE, RACE, GOAL) are never translated."""
        desc = "Easy running 6-8x( 15s strides )"

        respx_mock.post(EVENTS_URL).mock(
            return_value=Response(200, json=_make_event_response(category="NOTE", description=desc))
        )

        result = await create_event(
            start_date="2026-04-10",
            name="Race note",
            category="NOTE",
            description=desc,
            duration_seconds=3600,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        assert "description_translated" not in response["metadata"]

    async def test_sport_type_ride_uses_power_context(self, mock_config, respx_mock):
        """Ride events pass sport_type='Ride' to the translator (no crash)."""
        desc = "30min easy"

        respx_mock.post(EVENTS_URL).mock(
            return_value=Response(
                200,
                json=_make_event_response(event_type="Ride", description="- 30m z2 pace"),
            )
        )

        result = await create_event(
            start_date="2026-04-10",
            name="Easy Ride",
            category="WORKOUT",
            description=desc,
            event_type="Ride",
            duration_seconds=1800,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        assert "data" in response
        assert response["data"]["type"] == "Ride"


# ---------------------------------------------------------------------------
# create_event — auto_translate=False
# ---------------------------------------------------------------------------


class TestCreateEventNoTranslate:
    """create_event with auto_translate=False."""

    async def test_description_sent_verbatim(self, mock_config, respx_mock):
        """When auto_translate=False, the raw description reaches the API unchanged."""
        finalsurge_desc = "Easy running throughout 7x( 17s @ Stride / Full recovery easy jog )"

        captured: dict = {}

        def _capture_handler(request):
            captured["body"] = json.loads(request.content)
            return Response(
                200,
                json=_make_event_response(description=finalsurge_desc),
            )

        respx_mock.post(EVENTS_URL).mock(side_effect=_capture_handler)

        await create_event(
            start_date="2026-04-10",
            name="Strides",
            category="WORKOUT",
            description=finalsurge_desc,
            event_type="Run",
            duration_seconds=2700,
            auto_translate=False,
            ctx=_make_ctx(mock_config),
        )

        assert captured["body"]["description"] == finalsurge_desc

    async def test_no_translation_metadata_in_response(self, mock_config, respx_mock):
        """No translation metadata is present when auto_translate=False."""
        respx_mock.post(EVENTS_URL).mock(
            return_value=Response(200, json=_make_event_response())
        )

        result = await create_event(
            start_date="2026-04-10",
            name="Easy Run",
            category="WORKOUT",
            description="30min easy",
            event_type="Run",
            duration_seconds=1800,
            auto_translate=False,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        assert "description_translated" not in response["metadata"]


# ---------------------------------------------------------------------------
# bulk_create_events — auto_translate
# ---------------------------------------------------------------------------


class TestBulkCreateEventsAutoTranslate:
    """bulk_create_events with and without auto_translate."""

    def _make_bulk_payload(self) -> list[dict]:
        return [
            {
                "start_date_local": "2026-04-10",
                "name": "Strides Run",
                "category": "WORKOUT",
                "type": "Run",
                "description": "Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )",
                "moving_time": 2700,
            },
            {
                "start_date_local": "2026-04-11",
                "name": "Easy Run",
                "category": "WORKOUT",
                "type": "Run",
                "description": "30min easy",
                "moving_time": 1800,
            },
            {
                "start_date_local": "2026-04-12",
                "name": "Race Note",
                "category": "NOTE",
                "description": "Remember to bring gels",
            },
        ]

    async def test_translates_eligible_workout_events(self, mock_config, respx_mock):
        """Eligible WORKOUT events have their descriptions translated; NOTE is untouched."""
        payload = self._make_bulk_payload()
        captured: dict = {}

        def _capture_handler(request):
            captured["body"] = json.loads(request.content)
            # Echo back minimal event objects
            return Response(
                200,
                json=[
                    _make_event_response(event_id=i + 1, description=e.get("description"))
                    for i, e in enumerate(captured["body"])
                ],
            )

        respx_mock.post(BULK_EVENTS_URL).mock(side_effect=_capture_handler)

        result = await bulk_create_events(
            events=json.dumps(payload),
            auto_translate=True,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        assert "data" in response

        # The strides workout (index 0) should have been translated
        sent_events = captured["body"]
        strides_desc = sent_events[0]["description"]
        assert "7x" in strides_desc, f"Expected 7x block, got:\n{strides_desc}"
        assert "- 17s z5 pace" in strides_desc

        # The easy run (index 1) — "30min easy" → single step, may or may not change
        # Just verify it didn't crash and is a string
        assert isinstance(sent_events[1]["description"], str)

        # The NOTE (index 2) must be untouched
        assert sent_events[2]["description"] == "Remember to bring gels"

        # translated_count must be at least 1 (the strides workout)
        assert response["metadata"]["translated_count"] >= 1

    async def test_no_translation_when_flag_false(self, mock_config, respx_mock):
        """With auto_translate=False all descriptions reach the API verbatim."""
        payload = self._make_bulk_payload()
        captured: dict = {}

        def _capture_handler(request):
            captured["body"] = json.loads(request.content)
            return Response(
                200,
                json=[
                    _make_event_response(event_id=i + 1)
                    for i in range(len(captured["body"]))
                ],
            )

        respx_mock.post(BULK_EVENTS_URL).mock(side_effect=_capture_handler)

        await bulk_create_events(
            events=json.dumps(payload),
            auto_translate=False,
            ctx=_make_ctx(mock_config),
        )

        original_descs = [e.get("description") for e in payload]
        sent_descs = [e.get("description") for e in captured["body"]]
        assert sent_descs == original_descs

    async def test_translated_count_zero_when_no_eligible_events(
        self, mock_config, respx_mock
    ):
        """translated_count is 0 when no events qualify for translation."""
        payload = [
            {
                "start_date_local": "2026-04-10",
                "name": "Easy Run",
                "category": "WORKOUT",
                "type": "Run",
                # No description → not eligible
                "moving_time": 1800,
            }
        ]

        respx_mock.post(BULK_EVENTS_URL).mock(
            return_value=Response(200, json=[_make_event_response()])
        )

        result = await bulk_create_events(
            events=json.dumps(payload),
            auto_translate=True,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        assert response["metadata"]["translated_count"] == 0

    async def test_inline_repeat_pattern_in_bulk(self, mock_config, respx_mock):
        """The inline 'N x work and recovery' pattern is translated in bulk mode."""
        payload = [
            {
                "start_date_local": "2026-04-10",
                "name": "MP Intervals",
                "category": "WORKOUT",
                "type": "Run",
                "description": "8 x 4:00mins @MP->HMP and 2:00mins easy",
                "moving_time": 4800,
            }
        ]
        captured: dict = {}

        def _capture_handler(request):
            captured["body"] = json.loads(request.content)
            return Response(200, json=[_make_event_response()])

        respx_mock.post(BULK_EVENTS_URL).mock(side_effect=_capture_handler)

        result = await bulk_create_events(
            events=json.dumps(payload),
            auto_translate=True,
            ctx=_make_ctx(mock_config),
        )

        response = json.loads(result)
        sent_desc = captured["body"][0]["description"]
        assert "8x" in sent_desc
        assert "- 4m z4 pace" in sent_desc
        assert response["metadata"]["translated_count"] == 1
