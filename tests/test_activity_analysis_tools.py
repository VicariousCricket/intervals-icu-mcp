"""Tests for activity analysis tools (streams and best efforts)."""

import json
from unittest.mock import MagicMock

from httpx import Response

from intervals_icu_mcp.auth import ICUConfig
from intervals_icu_mcp.tools.activity_analysis import get_activity_streams, get_best_efforts


class TestGetActivityStreams:
    """Tests for get_activity_streams tool."""

    async def test_streams_written_to_disk_not_inlined(
        self,
        respx_mock,
        tmp_path,
    ):
        """Stream arrays must be written to a file, not returned inline in the response."""
        config = ICUConfig(
            intervals_icu_api_key="test_api_key_12345",
            intervals_icu_athlete_id="i123456",
            intervals_icu_stream_cache_dir=str(tmp_path),
        )
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = config

        # A small run stream - the exact case that used to slip past host-side disk routing.
        raw_streams = [
            {"type": "heartrate", "data": [140, 141, 142]},
            {"type": "watts", "data": [200, 210, 205]},
        ]
        respx_mock.get("/activity/a1/streams").mock(return_value=Response(200, json=raw_streams))

        result = await get_activity_streams(activity_id="a1", ctx=mock_ctx)
        response = json.loads(result)

        assert "file_path" in response["data"]
        # The raw arrays themselves must not be inlined anywhere in the response.
        assert "streams" not in response["data"]
        assert "watts" not in response["data"]

        file_path = response["data"]["file_path"]
        written = json.loads(open(file_path, encoding="utf-8").read())
        assert written["heartrate"] == [140, 141, 142]
        assert written["watts"] == [200, 210, 205]

        assert response["data"]["stream_lengths"]["heartrate"] == 3
        assert set(response["data"]["available_streams"]) == {"heartrate", "watts"}

    async def test_cache_pruned_beyond_max_files(
        self,
        respx_mock,
        tmp_path,
    ):
        """Old cache files beyond the retention cap are cleaned up on write."""
        from intervals_icu_mcp.tools import activity_analysis as mod

        config = ICUConfig(
            intervals_icu_api_key="test_api_key_12345",
            intervals_icu_athlete_id="i123456",
            intervals_icu_stream_cache_dir=str(tmp_path),
        )
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = config

        # Pre-populate the cache dir with more files than the retention cap allows.
        tmp_path.mkdir(parents=True, exist_ok=True)
        original_cap = mod._STREAM_CACHE_MAX_FILES
        mod._STREAM_CACHE_MAX_FILES = 3
        try:
            for i in range(5):
                f = tmp_path / f"old{i}_streams_{i}.json"
                f.write_text("{}")

            respx_mock.get("/activity/a1/streams").mock(
                return_value=Response(200, json=[{"type": "watts", "data": [1, 2, 3]}])
            )
            await get_activity_streams(activity_id="a1", ctx=mock_ctx)

            remaining = list(tmp_path.glob("*_streams_*.json"))
            assert len(remaining) <= mod._STREAM_CACHE_MAX_FILES
        finally:
            mod._STREAM_CACHE_MAX_FILES = original_cap


class TestGetBestEfforts:
    """Tests for get_best_efforts tool."""

    async def test_best_efforts_populated(
        self,
        mock_config,
        respx_mock,
    ):
        """A realistic response must surface non-null average/duration values."""
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        respx_mock.get("/activity/a1/best-efforts").mock(
            return_value=Response(
                200,
                json={
                    "efforts": [
                        {
                            "start_index": 20244,
                            "end_index": 20544,
                            "average": 221.38333,
                            "duration": 300,
                            "distance": None,
                        }
                    ]
                },
            )
        )

        result = await get_best_efforts(activity_id="a1", stream="watts", ctx=mock_ctx)
        response = json.loads(result)

        assert response["data"]["count"] == 1
        effort = response["data"]["best_efforts"][0]
        assert effort["average_watts"] == 221.38333
        assert effort["duration_seconds"] == 300

    async def test_all_null_average_fails_loudly(
        self,
        mock_config,
        respx_mock,
    ):
        """If every effort comes back with a null average, surface an error instead of nulls."""
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        respx_mock.get("/activity/a1/best-efforts").mock(
            return_value=Response(
                200,
                json={
                    "efforts": [
                        {"start_index": 0, "end_index": 300, "average": None, "duration": None},
                    ]
                },
            )
        )

        result = await get_best_efforts(activity_id="a1", stream="watts", ctx=mock_ctx)
        response = json.loads(result)

        assert "error" in response
        assert response["error"]["type"] == "data_integrity_error"

    async def test_count_param_forwarded(
        self,
        mock_config,
        respx_mock,
    ):
        """Explicit count must be sent through to the API."""
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        route = respx_mock.get("/activity/a1/best-efforts").mock(
            return_value=Response(
                200,
                json={
                    "efforts": [
                        {"start_index": 0, "end_index": 300, "average": 200.0, "duration": 300}
                    ]
                },
            )
        )

        await get_best_efforts(activity_id="a1", stream="watts", count=1, ctx=mock_ctx)

        assert route.calls.last.request.url.params["count"] == "1"
