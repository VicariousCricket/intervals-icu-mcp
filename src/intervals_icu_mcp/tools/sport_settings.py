"""Sport-specific settings tools for FTP, FTHR, pace thresholds, and zones."""

from typing import Annotated, Any

from fastmcp import Context

from ..auth import load_config, validate_credentials
from ..client import ICUAPIError, ICUClient
from ..response_builder import ResponseBuilder
from .types import IntParam, OptionalIntParam


async def get_sport_settings(
    ctx: Context | None = None,
) -> str:
    """Get all sport-specific settings (FTP, FTHR, pace thresholds, zones).

    Returns:
        Formatted list of sport settings with thresholds and zones
    """
    config = load_config()
    if not validate_credentials(config):
        return (
            "Error: Intervals.icu credentials not configured. Run intervals-icu-mcp-auth to set up."
        )

    try:
        async with ICUClient(config) as client:
            settings_list = await client.get_sport_settings()

            if not settings_list:
                return ResponseBuilder.build_response(
                    {"message": "No sport settings found"}, metadata={"count": 0}
                )

            settings_data: list[dict[str, Any]] = []

            for settings in settings_list:
                sport_info: dict[str, Any] = {
                    "id": settings.id,
                    "types": settings.types,
                }

                # Power settings (cycling)
                if settings.ftp is not None:
                    sport_info["ftp_watts"] = settings.ftp

                # Heart rate settings
                if settings.lthr is not None:
                    sport_info["lthr_bpm"] = settings.lthr

                # Pace settings (running/swimming)
                if settings.threshold_pace is not None:
                    pace_secs = settings.threshold_pace * 60
                    minutes = int(pace_secs // 60)
                    seconds = int(pace_secs % 60)
                    unit = "/100m" if settings.pace_units == "SECS_100M" else "/km"
                    sport_info["threshold_pace"] = f"{minutes}:{seconds:02d} {unit}"

                settings_data.append(sport_info)

            return ResponseBuilder.build_response(
                {"sport_settings": settings_data},
                metadata={"count": len(settings_list), "type": "sport_settings_list"},
            )

    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(str(e), error_type="unexpected_error")


async def update_sport_settings(
    sport_id: Annotated[IntParam, "ID of the sport settings to update"],
    ftp: Annotated[OptionalIntParam, "Functional Threshold Power in watts (for cycling)"] = None,
    fthr: Annotated[OptionalIntParam, "Functional Threshold Heart Rate in bpm"] = None,
    pace_threshold: Annotated[
        float | None, "Threshold pace in min/km (e.g., 4.5 for 4:30/km)"
    ] = None,
    swim_threshold: Annotated[
        float | None, "Swim threshold in min/100m (e.g., 1.5 for 1:30/100m)"
    ] = None,
    ctx: Context | None = None,
) -> str:
    """Update sport-specific settings (FTP, FTHR, pace thresholds).

    Args:
        sport_id: ID of the sport settings to update
        ftp: Functional Threshold Power in watts (optional)
        fthr: Functional Threshold Heart Rate in bpm (optional)
        pace_threshold: Threshold pace in min/km (optional)
        swim_threshold: Swim threshold in min/100m (optional)

    Returns:
        Updated sport settings
    """
    config = load_config()
    if not validate_credentials(config):
        return (
            "Error: Intervals.icu credentials not configured. Run intervals-icu-mcp-auth to set up."
        )

    try:
        async with ICUClient(config) as client:
            settings_data: dict[str, Any] = {}

            if ftp is not None:
                settings_data["ftp"] = ftp
            if fthr is not None:
                settings_data["fthr"] = fthr
            if pace_threshold is not None:
                settings_data["pace_threshold"] = pace_threshold
            if swim_threshold is not None:
                settings_data["swim_threshold"] = swim_threshold

            if not settings_data:
                return ResponseBuilder.build_error_response(
                    "No fields provided to update", error_type="validation_error"
                )

            settings = await client.update_sport_settings(sport_id, settings_data)

            result: dict[str, Any] = {
                "id": settings.id,
                "types": settings.types,
            }

            if settings.ftp is not None:
                result["ftp_watts"] = settings.ftp
            if settings.lthr is not None:
                result["lthr_bpm"] = settings.lthr
            if settings.threshold_pace is not None:
                pace_secs = settings.threshold_pace * 60
                minutes = int(pace_secs // 60)
                seconds = int(pace_secs % 60)
                unit = "/100m" if settings.pace_units == "SECS_100M" else "/km"
                result["threshold_pace"] = f"{minutes}:{seconds:02d} {unit}"

            return ResponseBuilder.build_response(
                result,
                metadata={
                    "type": "sport_settings_updated",
                    "message": "Sport settings updated successfully",
                },
            )

    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(str(e), error_type="unexpected_error")


async def apply_sport_settings(
    sport_id: Annotated[IntParam, "ID of the sport settings to apply"],
    oldest_date: Annotated[
        str | None, "Oldest date to apply settings to (YYYY-MM-DD format)"
    ] = None,
    ctx: Context | None = None,
) -> str:
    """Apply sport settings (zones, thresholds) to historical activities.

    This recalculates training load, zones, and other derived metrics for activities
    based on the current sport settings.

    Args:
        sport_id: ID of the sport settings to apply
        oldest_date: Oldest date to apply settings to (optional, defaults to all)

    Returns:
        Result of applying settings
    """
    config = load_config()
    if not validate_credentials(config):
        return (
            "Error: Intervals.icu credentials not configured. Run intervals-icu-mcp-auth to set up."
        )

    try:
        async with ICUClient(config) as client:
            result = await client.apply_sport_settings(sport_id, oldest=oldest_date)

            return ResponseBuilder.build_response(
                result,
                metadata={
                    "type": "sport_settings_applied",
                    "message": "Sport settings applied to activities successfully",
                },
            )

    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(str(e), error_type="unexpected_error")


async def create_sport_settings(
    sport_type: Annotated[str, "Type of sport (e.g., 'Ride', 'Run', 'Swim')"],
    ftp: Annotated[OptionalIntParam, "Functional Threshold Power in watts (for cycling)"] = None,
    fthr: Annotated[OptionalIntParam, "Functional Threshold Heart Rate in bpm"] = None,
    pace_threshold: Annotated[
        float | None, "Threshold pace in min/km (e.g., 4.5 for 4:30/km)"
    ] = None,
    swim_threshold: Annotated[
        float | None, "Swim threshold in min/100m (e.g., 1.5 for 1:30/100m)"
    ] = None,
    ctx: Context | None = None,
) -> str:
    """Create new sport-specific settings.

    Args:
        sport_type: Type of sport (e.g., 'Ride', 'Run', 'Swim')
        ftp: Functional Threshold Power in watts (optional)
        fthr: Functional Threshold Heart Rate in bpm (optional)
        pace_threshold: Threshold pace in min/km (optional)
        swim_threshold: Swim threshold in min/100m (optional)

    Returns:
        Created sport settings
    """
    config = load_config()
    if not validate_credentials(config):
        return (
            "Error: Intervals.icu credentials not configured. Run intervals-icu-mcp-auth to set up."
        )

    try:
        async with ICUClient(config) as client:
            settings_data: dict[str, Any] = {"type": sport_type}

            if ftp is not None:
                settings_data["ftp"] = ftp
            if fthr is not None:
                settings_data["fthr"] = fthr
            if pace_threshold is not None:
                settings_data["pace_threshold"] = pace_threshold
            if swim_threshold is not None:
                settings_data["swim_threshold"] = swim_threshold

            settings = await client.create_sport_settings(settings_data)

            result: dict[str, Any] = {
                "id": settings.id,
                "types": settings.types,
            }

            if settings.ftp is not None:
                result["ftp_watts"] = settings.ftp
            if settings.lthr is not None:
                result["lthr_bpm"] = settings.lthr
            if settings.threshold_pace is not None:
                pace_secs = settings.threshold_pace * 60
                minutes = int(pace_secs // 60)
                seconds = int(pace_secs % 60)
                unit = "/100m" if settings.pace_units == "SECS_100M" else "/km"
                result["threshold_pace"] = f"{minutes}:{seconds:02d} {unit}"

            return ResponseBuilder.build_response(
                result,
                metadata={
                    "type": "sport_settings_created",
                    "message": "Sport settings created successfully",
                },
            )

    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(str(e), error_type="unexpected_error")


async def delete_sport_settings(
    sport_id: Annotated[IntParam, "ID of the sport settings to delete"],
    ctx: Context | None = None,
) -> str:
    """Delete sport-specific settings.

    Args:
        sport_id: ID of the sport settings to delete

    Returns:
        Deletion confirmation
    """
    config = load_config()
    if not validate_credentials(config):
        return (
            "Error: Intervals.icu credentials not configured. Run intervals-icu-mcp-auth to set up."
        )

    try:
        async with ICUClient(config) as client:
            await client.delete_sport_settings(sport_id)

            return ResponseBuilder.build_response(
                {"sport_id": sport_id, "deleted": True},
                metadata={
                    "type": "sport_settings_deleted",
                    "message": "Sport settings deleted successfully",
                },
            )

    except ICUAPIError as e:
        return ResponseBuilder.build_error_response(e.message, error_type="api_error")
    except Exception as e:
        return ResponseBuilder.build_error_response(str(e), error_type="unexpected_error")
