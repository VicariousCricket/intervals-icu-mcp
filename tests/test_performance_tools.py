"""Tests for performance (power curve) tools."""

import json
from unittest.mock import MagicMock

from httpx import Response

from intervals_icu_mcp.tools.performance import get_power_curves


class TestGetPowerCurves:
    """Tests for get_power_curves tool."""

    async def test_empty_result_reports_exact_queried_range(
        self,
        mock_config,
        respx_mock,
    ):
        """An empty power curve must say exactly what was searched, not just "not found"."""
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        respx_mock.get("/athlete/i123456/activity-power-curves").mock(
            return_value=Response(200, json={"secs": [], "curves": []})
        )

        result = await get_power_curves(activity_type="Run", ctx=mock_ctx)
        response = json.loads(result)

        message = response["metadata"]["message"]
        assert "Run" in message
        assert response["metadata"]["queried_activity_type"] == "Run"
        assert response["metadata"]["queried_newest"] is not None
        assert response["metadata"]["queried_oldest"] is not None

    async def test_newest_forwarded_to_api(
        self,
        mock_config,
        respx_mock,
    ):
        """The tool must send an explicit `newest` rather than relying on client-side defaults."""
        route = respx_mock.get("/athlete/i123456/activity-power-curves").mock(
            return_value=Response(200, json={"secs": [], "curves": []})
        )
        mock_ctx = MagicMock()
        mock_ctx.get_state.return_value = mock_config

        await get_power_curves(ctx=mock_ctx)

        assert "newest" in route.calls.last.request.url.params
