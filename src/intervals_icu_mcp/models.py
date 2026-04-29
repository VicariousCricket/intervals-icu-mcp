"""Pydantic models for Intervals.icu API responses."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Type aliases for common enums
ActivityType = Literal["Ride", "Run", "Swim", "Walk", "Hike", "VirtualRide", "VirtualRun", "Other"]
EventCategory = Literal["WORKOUT", "NOTE", "RACE", "GOAL"]


# ==================== Athlete Models ====================


class SportSettings(BaseModel):
    """Sport-specific settings for an athlete."""

    id: int
    type: str | None = None  # singular sport type from API (e.g. "Ride")
    types: list[str] = Field(default_factory=list)  # multi-type variant
    ftp: int | None = None
    lthr: int | None = None
    threshold_pace: float | None = None
    pace_units: str | None = None


class Athlete(BaseModel):
    """Full athlete profile information."""

    id: str
    name: str
    email: str | None = None
    weight: float | None = None
    dob: str | None = None
    sex: str | None = None
    created: datetime | None = None
    ctl: float | None = None
    atl: float | None = None
    tsb: float | None = None
    ramp_rate: float | None = None
    sport_settings: list[SportSettings] = Field(default_factory=list[SportSettings])


class AthleteProfile(BaseModel):
    """Simplified athlete profile."""

    id: str
    name: str
    email: str | None = None
    weight: float | None = None
    ctl: float | None = None
    atl: float | None = None
    tsb: float | None = None


# ==================== Activity Models ====================


class ActivitySummary(BaseModel):
    """Summary representation of an activity (for lists)."""

    id: str
    start_date_local: datetime
    name: str | None = None
    type: str | None = None
    distance: float | None = None
    moving_time: int | None = None
    elapsed_time: int | None = None
    total_elevation_gain: float | None = None
    average_speed: float | None = None
    average_heartrate: int | None = None
    average_watts: int | None = None
    normalized_power: int | None = None
    average_cadence: float | None = None
    icu_training_load: int | None = None
    icu_intensity: float | None = None


class Activity(ActivitySummary):
    """Detailed activity with full information."""

    athlete_id: str | None = None
    description: str | None = None
    calories: int | None = None
    carbs_ingested: int | None = None
    device_name: str | None = None
    max_heartrate: int | None = None
    max_speed: float | None = None
    max_watts: int | None = None
    max_cadence: float | None = None
    weighted_average_watts: int | None = None
    variability_index: float | None = None
    efficiency_factor: float | None = None
    tss: float | None = None
    hrss: float | None = None
    trimp: float | None = None
    feel: int | None = None
    perceived_exertion: int | None = None
    compliance: float | None = None
    avg_lr_balance: float | None = None
    commute: bool | None = None
    trainer: bool | None = None
    indoor: bool | None = None
    analyzed: str | None = None


class ActivitySearchResult(BaseModel):
    """Search result for activities."""

    id: str
    name: str | None = None
    start_date_local: datetime
    type: str | None = None
    distance: float | None = None
    moving_time: int | None = None


# ==================== Wellness Models ====================


class Wellness(BaseModel):
    """Wellness record with health metrics."""

    id: str  # ISO-8601 date
    weight: float | None = None
    resting_hr: int | None = Field(None, alias="restingHR")
    hrv: float | None = None
    hrv_sdnn: float | None = Field(None, alias="hrvSDNN")
    sleep_secs: int | None = Field(None, alias="sleepSecs")
    sleep_quality: int | None = Field(None, alias="sleepQuality")
    sleep_score: float | None = Field(None, alias="sleepScore")
    avg_sleeping_hr: float | None = Field(None, alias="avgSleepingHR")
    fatigue: int | None = None
    soreness: int | None = None
    stress: int | None = None
    mood: int | None = None
    motivation: int | None = None
    injury: int | None = None
    spo2: float | None = None
    respiration: float | None = None
    hydration: int | None = None
    hydration_volume: float | None = Field(None, alias="hydrationVolume")
    kcal_consumed: int | None = Field(None, alias="kcalConsumed")
    menstrual_phase: str | None = Field(None, alias="menstrualPhase")
    systolic: int | None = None
    diastolic: int | None = None
    blood_glucose: float | None = Field(None, alias="bloodGlucose")
    lactate: float | None = None
    body_fat: float | None = Field(None, alias="bodyFat")
    readiness: float | None = None
    baevsky_si: float | None = Field(None, alias="baevskySI")
    steps: int | None = None
    comments: str | None = None
    ctl: float | None = None
    atl: float | None = None
    tsb: float | None = None  # Training Stress Balance
    ctl_load: float | None = Field(None, alias="ctlLoad")
    atl_load: float | None = Field(None, alias="atlLoad")
    ramp_rate: float | None = Field(None, alias="rampRate")
    updated: datetime | None = None

    model_config = ConfigDict(populate_by_name=True)


# ==================== Event/Calendar Models ====================


class Event(BaseModel):
    """Calendar event (planned workout, note, race, etc.)."""

    id: int
    start_date_local: str  # ISO-8601 date
    category: str | None = None  # WORKOUT, NOTE, RACE, GOAL
    name: str | None = None
    description: str | None = None
    type: str | None = None
    distance: float | None = None
    distance_target: float | None = None
    moving_time: int | None = None
    icu_training_load: int | None = Field(None, alias="icu_training_load")
    icu_intensity: float | None = Field(None, alias="icu_intensity")
    icu_atl: float | None = Field(None, alias="icu_atl")
    icu_ctl: float | None = Field(None, alias="icu_ctl")
    joules: int | None = None
    joules_above_ftp: int | None = Field(None, alias="joules_above_ftp")
    color: str | None = None
    hide_from_athlete: bool | None = Field(None, alias="hide_from_athlete")
    athlete_cannot_edit: bool | None = Field(None, alias="athlete_cannot_edit")
    external_id: str | None = Field(None, alias="external_id")
    created_by_id: str | None = Field(None, alias="created_by_id")

    model_config = ConfigDict(populate_by_name=True)


# ==================== Workout Library Models ====================


class Workout(BaseModel):
    """Workout from library."""

    id: int
    athlete_id: str | None = Field(None, alias="athlete_id")
    name: str | None = None
    description: str | None = None
    folder_id: int | None = Field(None, alias="folder_id")
    moving_time: int | None = Field(None, alias="moving_time")
    distance: float | None = None
    icu_training_load: int | None = Field(None, alias="icu_training_load")
    icu_intensity: float | None = Field(None, alias="icu_intensity")
    joules: int | None = None
    joules_above_ftp: int | None = Field(None, alias="joules_above_ftp")
    indoor: bool | None = None
    color: str | None = None
    type: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class Folder(BaseModel):
    """Workout folder or training plan."""

    id: int
    athlete_id: str | None = Field(None, alias="athlete_id")
    name: str | None = None
    description: str | None = None
    num_workouts: int | None = Field(None, alias="num_workouts")
    start_date_local: str | None = Field(None, alias="start_date_local")
    duration_weeks: int | None = Field(None, alias="duration_weeks")
    hours_per_week_min: int | None = Field(None, alias="hours_per_week_min")
    hours_per_week_max: int | None = Field(None, alias="hours_per_week_max")

    model_config = ConfigDict(populate_by_name=True)


# ==================== Power Curve Models ====================


class DataCurvePt(BaseModel):
    """Single point on a power/HR/pace curve."""

    secs: int  # Duration in seconds
    watts: int | None = None  # For power curves
    bpm: int | None = None  # For HR curves
    pace: float | None = None  # For pace curves (min/km)
    src_activity_id: str | None = None  # Activity where this effort occurred
    date: str | None = None  # Date of the effort


class PowerCurve(BaseModel):
    """Power curve data for an athlete."""

    name: str | None = None
    type: str | None = None
    athlete_id: str | None = None
    data: list[DataCurvePt] = Field(default_factory=list[DataCurvePt])


class HRCurve(BaseModel):
    """Heart rate curve data for an athlete."""

    name: str | None = None
    type: str | None = None
    athlete_id: str | None = None
    data: list[DataCurvePt] = Field(default_factory=list[DataCurvePt])


class PaceCurve(BaseModel):
    """Pace curve data for an athlete."""

    name: str | None = None
    type: str | None = None
    athlete_id: str | None = None
    data: list[DataCurvePt] = Field(default_factory=list[DataCurvePt])


# ==================== Training Plan Models ====================


class AthleteTrainingPlan(BaseModel):
    """Athlete's current training plan."""

    athlete_id: str | None = Field(None, alias="athlete_id")
    folder_id: int | None = Field(None, alias="folder_id")
    plan_name: str | None = Field(None, alias="plan_name")
    start_date_local: str | None = Field(None, alias="start_date_local")
    end_date_local: str | None = Field(None, alias="end_date_local")
    weeks_remaining: int | None = Field(None, alias="weeks_remaining")

    model_config = ConfigDict(populate_by_name=True)


# ==================== Generic Response Models ====================


class APIError(BaseModel):
    """Error response from API."""

    message: str
    status_code: int | None = None


# ==================== Supporting Models ====================


class FitnessSummary(BaseModel):
    """Custom model for aggregated fitness metrics."""

    ctl: float | None = None  # Chronic Training Load (Fitness)
    atl: float | None = None  # Acute Training Load (Fatigue)
    tsb: float | None = None  # Training Stress Balance (Form)
    ramp_rate: float | None = None  # Rate of fitness change
    date: str | None = None
    interpretation: dict[str, Any] = Field(default_factory=dict)


# ==================== Activity Interval Models ====================


class Interval(BaseModel):
    """Activity interval data (maps to API Interval schema)."""

    id: int | None = None
    type: str | None = None  # e.g., "WORK", "REST", "WARM_UP", "COOL_DOWN"
    start_index: int | None = None  # Sample index in the data stream
    end_index: int | None = None
    start_time: int | None = None  # Seconds from activity start
    end_time: int | None = None
    moving_time: int | None = None  # Duration in seconds (moving)
    elapsed_time: int | None = None  # Duration in seconds (total)
    distance: float | None = None
    average_watts: int | None = None
    weighted_average_watts: int | None = None  # Normalized power
    average_heartrate: int | None = None
    max_heartrate: int | None = None
    average_cadence: float | None = None
    average_speed: float | None = None
    training_load: float | None = None
    label: str | None = None


# ==================== Activity Streams Models ====================


class ActivityStreams(BaseModel):
    """Time-series data streams for an activity."""

    watts: list[int | None] | None = None
    heartrate: list[int | None] | None = None
    cadence: list[int | None] | None = None
    velocity_smooth: list[float | None] | None = None
    altitude: list[float | None] | None = None
    distance: list[float | None] | None = None
    time: list[int | None] | None = None
    latlng: list[list[float] | None] | None = None
    temp: list[int | None] | None = None
    moving: list[bool | None] | None = None
    grade_smooth: list[float | None] | None = None


# ==================== Best Efforts Models ====================


class BestEffort(BaseModel):
    """Best effort for a specific duration (maps to API Effort schema)."""

    start_index: int | None = None
    end_index: int | None = None
    average: float | None = None  # Mean value of the requested stream (watts, bpm, or m/s)
    duration: int | None = None  # Duration in seconds
    distance: float | None = None


# ==================== Gear Models ====================


class GearReminder(BaseModel):
    """Gear maintenance reminder (maps to API GearReminder schema)."""

    id: int
    gear_id: str | None = None
    name: str | None = None  # Reminder name/description
    distance: float | None = None  # Distance threshold in meters
    time: float | None = None  # Time threshold in seconds
    activities: int | None = None  # Activity count threshold
    days: int | None = None  # Days threshold
    last_reset: str | None = None
    snoozed_until: str | None = None
    percent_used: float | None = None  # How much of threshold has been used (0-100+)
    distance_used: float | None = None  # Distance used since last reset (meters)
    time_used: float | None = None  # Time used since last reset (seconds)
    activities_used: int | None = None
    days_used: int | None = None


class Gear(BaseModel):
    """Gear/equipment item (maps to API Gear schema)."""

    id: str
    athlete_id: str | None = None
    name: str | None = None
    gear_type: str | None = Field(None, alias="type")  # API field is "type"
    distance: float | None = None  # Total distance in meters
    time: float | None = None  # Total time in seconds
    activities: int | None = None  # Total activity count
    retired: str | None = None  # Retirement date if retired, else None
    notes: str | None = None
    reminders: list[GearReminder] = Field(default_factory=list[GearReminder])

    model_config = ConfigDict(populate_by_name=True)


# ==================== Histogram Models ====================


class HistogramBin(BaseModel):
    """Single bin in a histogram."""

    min: float  # Minimum value for this bin
    max: float  # Maximum value for this bin
    count: int | None = None  # Number of data points in this bin
    secs: int | None = None  # Time spent in this bin (seconds)


class Histogram(BaseModel):
    """Histogram data for activity metrics."""

    bins: list[HistogramBin] = Field(default_factory=list[HistogramBin])
    total_count: int | None = None
    total_secs: int | None = None
