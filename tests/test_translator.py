"""Tests for the FinalSurge → Intervals.icu workout translator."""

import pytest

from intervals_icu_mcp.workout_translator import (
    _seconds_to_icu,
    _map_intensity,
    translate_workout,
)


# ---------------------------------------------------------------------------
# Unit: duration formatting
# ---------------------------------------------------------------------------


def test_seconds_to_icu_seconds_only():
    assert _seconds_to_icu(17) == "17s"


def test_seconds_to_icu_minutes_only():
    assert _seconds_to_icu(600) == "10m"


def test_seconds_to_icu_minutes_and_seconds():
    assert _seconds_to_icu(105) == "1m45s"


def test_seconds_to_icu_hours_minutes_seconds():
    assert _seconds_to_icu(3750) == "1h2m30s"


def test_seconds_to_icu_zero():
    assert _seconds_to_icu(0) == "0s"


# ---------------------------------------------------------------------------
# Unit: intensity mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("easy", "z2 pace"),
        ("Easy", "z2 pace"),
        ("recovery", "z1 pace"),
        ("stride", "z5 pace"),
        ("fast", "z5 pace"),
        ("threshold", "z4 pace"),
        ("HMP", "z4 pace"),
        ("tempo", "z3 pace"),
        ("sprint", "z6 pace"),
        ("z3", "z3 pace"),
        ("Z5", "z5 pace"),
        ("Z1-Z2", "z2 pace"),
        ("unknown_term", "z2 pace"),  # default
    ],
)
def test_intensity_mapping(raw, expected):
    assert _map_intensity(raw) == expected


# ---------------------------------------------------------------------------
# Integration: translate_workout (design doc test cases)
# ---------------------------------------------------------------------------


def test_simple_easy_run():
    result = translate_workout("30min easy", 1800)
    assert result == "- 30m z2 pace"


def test_strides_workout():
    """6-8x strides → 7x, 15-20s → 17s, inferred full recovery."""
    description = "Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )"
    result = translate_workout(description, duration_seconds=2700)

    lines = result.strip().splitlines()
    # Find the Nx line index
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    # Blank line precedes interval block
    assert lines[nx_idx - 1] == ""
    # Optional base run before blank line
    if nx_idx >= 2:
        assert lines[0].startswith("- ")
        assert "z2 pace" in lines[0]
    # Repeat count
    assert lines[nx_idx] == "7x"
    # Work step
    assert lines[nx_idx + 1] == "- 17s z5 pace"
    # Recovery step exists and has z1/z2 intensity (inferred from "easy jog")
    assert lines[nx_idx + 2].startswith("- ")
    assert "z2 pace" in lines[nx_idx + 2] or "z1 pace" in lines[nx_idx + 2]


def test_structured_warmup_intervals_cooldown():
    """15:00 warm-up, 2x(10:00 @ HMP, 5:00 recovery), 5:00 cooldown."""
    description = "15:00 Easy (Z1-Z2) 2x( 10:00 @ HMP (Z4) 5:00 Walk / Easy Jog recovery ) 5:00 Easy (Z1-Z2)"
    result = translate_workout(description, duration_seconds=2700)

    lines = result.strip().splitlines()
    assert lines[0] == "- 15m z2 pace", f"Expected warmup, got: {lines[0]}"
    assert lines[1] == ""
    assert lines[2] == "2x"
    assert lines[3] == "- 10m z4 pace", f"Expected work step, got: {lines[3]}"
    assert lines[4] == "- 5m z2 pace", f"Expected recovery step, got: {lines[4]}"
    assert lines[5] == ""
    assert lines[6] == "- 5m z2 pace", f"Expected cooldown, got: {lines[6]}"


def test_translation_fallback_on_bad_input():
    """If description is completely unparseable, return original."""
    bad = "##@@@!!! no duration no intensity ###"
    result = translate_workout(bad, duration_seconds=1800)
    # Either returns original OR a valid fallback - should not raise
    assert isinstance(result, str)
    assert len(result) > 0


def test_range_reps_rounded_down():
    """4-6x → 5x (midpoint)."""
    description = "4-6x( 1m z4 pace / 2m z2 pace )"
    result = translate_workout(description, duration_seconds=1800)
    lines = result.strip().splitlines()
    # Find the Nx line
    nx_lines = [l for l in lines if re.fullmatch(r"\d+x", l.strip())]
    assert nx_lines, "Expected an Nx line"
    assert nx_lines[0] == "5x"


def test_threshold_intensity():
    description = "10min @threshold"
    result = translate_workout(description, duration_seconds=600)
    assert result == "- 10m z4 pace"


# ---------------------------------------------------------------------------
# Phase 3: inline "N x work [sep] recovery" prose/bullet patterns
# ---------------------------------------------------------------------------


def test_inline_repeat_with_arrow_intensity():
    """8 x 4:00mins @MP->HMP and 2:00mins easy → 8x block, @MP->HMP = z4 pace target."""
    # 8 × (4m work + 2m recovery) = 48m; total 1h20m → 32m base run
    description = "8 x 4:00mins @MP->HMP and 2:00mins easy"
    result = translate_workout(description, duration_seconds=4800)  # 1h20m

    lines = result.strip().splitlines()
    assert lines[0] == "- 32m z2 pace", f"Expected base run, got: {lines[0]}"
    assert lines[1] == ""
    assert lines[2] == "8x"
    assert lines[3] == "- 4m z4 pace", f"Expected work z4, got: {lines[3]}"
    assert lines[4] == "- 2m z2 pace", f"Expected recovery z2, got: {lines[4]}"


def test_inline_repeat_at_mp_with_rest():
    """4 x 15mins at MP with 5 mins rest → 4x block."""
    # 4 × (15m + 5m) = 80m; total 2h10m = 130m → 50m base run
    description = "4 x 15mins at MP with 5 mins rest"
    result = translate_workout(description, duration_seconds=7800)  # 2h10m

    lines = result.strip().splitlines()
    assert lines[0] == "- 50m z2 pace", f"Expected base run, got: {lines[0]}"
    assert lines[1] == ""
    assert lines[2] == "4x"
    assert lines[3] == "- 15m z3 pace", f"Expected work z3 (MP), got: {lines[3]}"
    assert lines[4] == "- 5m z1 pace", f"Expected recovery z1 (rest), got: {lines[4]}"


def test_inline_repeat_bullet_prefix():
    """Bullet-prefixed line: '- 8 x 4:00mins @MP' is recognised as an 8x block."""
    description = "- 8 x 4:00mins @MP"
    result = translate_workout(description, duration_seconds=4800)  # 1h20m

    lines = result.strip().splitlines()
    # Should have base run + blank + 8x + work step
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    assert lines[nx_idx] == "8x"
    assert lines[nx_idx + 1] == "- 4m z3 pace", f"Expected z3 (MP), got: {lines[nx_idx + 1]}"


def test_inline_repeat_range_reps():
    """6-8 x 4:00mins at HMP and 2:00mins easy → 7x (midpoint rounded down)."""
    description = "6-8 x 4:00mins at HMP and 2:00mins easy"
    result = translate_workout(description, duration_seconds=4200)  # 70m

    lines = result.strip().splitlines()
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    assert lines[nx_idx] == "7x"
    assert "z4 pace" in lines[nx_idx + 1]  # HMP = z4


def test_inline_repeat_no_recovery():
    """N x work with no recovery segment — no recovery step emitted."""
    description = "5 x 3:00mins @threshold"
    # 5 × 3m = 15m; total 30m → 15m base run
    result = translate_workout(description, duration_seconds=1800)

    lines = result.strip().splitlines()
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    assert lines[nx_idx] == "5x"
    assert lines[nx_idx + 1] == "- 3m z4 pace"
    # No recovery line after work step
    assert nx_idx + 2 == len(lines)


def test_mp_intensity_mapping():
    """'MP' and 'marathon pace' map to z3 pace."""
    from intervals_icu_mcp.workout_translator import _identify_intensity

    assert _identify_intensity("at MP", "Run") == "z3 pace"
    assert _identify_intensity("@MP", "Run") == "z3 pace"
    assert _identify_intensity("marathon pace", "Run") == "z3 pace"


def test_arrow_intensity_range():
    """'@MP->HMP' resolves to z4 pace (target/right side of arrow)."""
    from intervals_icu_mcp.workout_translator import _identify_intensity

    assert _identify_intensity("@MP->HMP", "Run") == "z4 pace"
    assert _identify_intensity("z3->z4", "Run") == "z4 pace"


import re  # noqa: E402 (used in tests above)


# ---------------------------------------------------------------------------
# Phase 5 pre-work: multi-line bullet-list parser
# ---------------------------------------------------------------------------


def test_bullet_list_pure_multi_step():
    """Pure bullet list with no Nx → one step per bullet."""
    description = (
        "- 20 mins warm up Easy\n"
        "- 20 mins at marathon pace\n"
        "- 5 mins easy jog\n"
        "- 10 mins at MP\n"
        "- 5 mins cool down"
    )
    result = translate_workout(description, duration_seconds=3600)
    lines = result.strip().splitlines()
    assert lines[0] == "- 20m z2 pace"
    assert lines[1] == "- 20m z3 pace"
    assert lines[2] == "- 5m z2 pace"
    assert lines[3] == "- 10m z3 pace"
    assert lines[4] == "- 5m z2 pace"
    assert len(lines) == 5


def test_bullet_list_full_75min_workout():
    """Full 7-bullet 75-min workout from translation doc."""
    description = (
        "- 20 mins warm up Easy\n"
        "- 20 mins at marathon pace (effort)\n"
        "- 5 mins easy jog or walking\n"
        "- 10 mins at marathon pace (effort)\n"
        "- 5 mins easy jog or walking\n"
        "- 5 mins at half marathon pace\n"
        "- 10 mins cool down easy"
    )
    result = translate_workout(description, duration_seconds=4500)
    lines = result.strip().splitlines()
    assert lines[0] == "- 20m z2 pace"
    assert lines[1] == "- 20m z3 pace"
    assert lines[2] == "- 5m z2 pace"
    assert lines[3] == "- 10m z3 pace"
    assert lines[4] == "- 5m z2 pace"
    assert lines[5] == "- 5m z4 pace"
    assert lines[6] == "- 10m z2 pace"
    assert len(lines) == 7


def test_bullet_list_with_embedded_nx():
    """Bullet list where one bullet contains a '2 x work with recovery' pattern."""
    description = (
        "- 45 mins easy\n"
        "- 2 x 40mins@MP with 10 mins easy rest in between\n"
        "- 15 mins easy"
    )
    result = translate_workout(description, duration_seconds=9000)
    lines = result.strip().splitlines()
    assert lines[0] == "- 45m z2 pace"
    assert lines[1] == ""
    assert lines[2] == "2x"
    assert lines[3] == "- 40m z3 pace"
    assert lines[4] == "- 10m z1 pace"  # "easy rest" → z1 (recovery, not z2)
    assert lines[5] == ""
    assert lines[6] == "- 15m z2 pace"


def test_bullet_list_embedded_nx_with_pace_annotation():
    """'2 x 40mins@MP(8:40-55)' — pace annotation in parens must not confuse parser."""
    description = (
        "- 45 mins easy\n"
        "- 2 x 40mins@MP(8:40-55) with 10 mins easy rest in between\n"
        "- 15 mins easy"
    )
    result = translate_workout(description, duration_seconds=9000)
    lines = result.strip().splitlines()
    assert lines[2] == "2x"
    assert lines[3] == "- 40m z3 pace"
    assert lines[4] == "- 10m z1 pace"  # "easy rest" → z1


def test_single_bullet_not_parsed_as_list():
    """A single bullet line must NOT activate the bullet-list parser."""
    result = translate_workout("- 8 x 4:00mins @MP", duration_seconds=4800)
    lines = result.strip().splitlines()
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    assert lines[nx_idx] == "8x"
    assert lines[nx_idx + 1] == "- 4m z3 pace"


# ---------------------------------------------------------------------------
# Strides / pickups template
# ---------------------------------------------------------------------------


def test_strides_keyword_applies_template():
    """'pickups' in description → 5x(15s z5 / 1m45s z1) template."""
    description = "Run 6-8 x 100m or 15-20s pickups, with full recovery"
    result = translate_workout(description, duration_seconds=1800)  # 30 min
    lines = result.strip().splitlines()
    # 30 min total − 10 min intervals = 20 min base run
    assert lines[0] == "- 20m z2 pace"
    assert lines[1] == ""
    assert lines[2] == "5x"
    assert lines[3] == "- 15s z5 pace"
    assert lines[4] == "- 1m45s z1 pace"


def test_strides_45min_workout():
    """Same description at 45 min → 35 min base run."""
    description = "Run 6-8 x 100m or 15-20s pickups, with full recovery"
    result = translate_workout(description, duration_seconds=2700)  # 45 min
    lines = result.strip().splitlines()
    assert lines[0] == "- 35m z2 pace"
    assert lines[2] == "5x"
    assert lines[3] == "- 15s z5 pace"
    assert lines[4] == "- 1m45s z1 pace"


def test_explicit_zone_in_strides_skips_template():
    """When description already has Z5 annotation, paren-form parser wins."""
    # This is the existing test_strides_workout scenario repackaged.
    description = "Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )"
    result = translate_workout(description, duration_seconds=2700)
    lines = result.strip().splitlines()
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    # Paren-form handled it: 7x, 17s z5
    assert lines[nx_idx] == "7x"
    assert lines[nx_idx + 1] == "- 17s z5 pace"


# ---------------------------------------------------------------------------
# Recovery intensity fix: 'easy jog rest' → z1, not z2
# ---------------------------------------------------------------------------


def test_recovery_jog_rest_maps_to_z1():
    """'walk/easy jog rest' in recovery segment → z1 pace, not z2."""
    description = "15 mins easy + 2 x 10mins at HMP with 5 mins walk/easy jog rest + 5 mins easy"
    result = translate_workout(description, duration_seconds=2700)
    lines = result.strip().splitlines()
    assert lines[0] == "- 15m z2 pace"
    assert lines[1] == ""
    assert lines[2] == "2x"
    assert lines[3] == "- 10m z4 pace"
    assert lines[4] == "- 5m z1 pace", f"Expected z1 recovery, got: {lines[4]}"


def test_easy_jog_rest_intensity():
    """Isolated check: 'easy jog rest' string resolves to z1 via INTENSITY_MAP."""
    from intervals_icu_mcp.workout_translator import _identify_intensity

    assert _identify_intensity("walk/easy jog rest", "Run") == "z1 pace"
    assert _identify_intensity("easy jog rest", "Run") == "z1 pace"
    assert _identify_intensity("walk rest", "Run") == "z1 pace"


# ---------------------------------------------------------------------------
# Phase 5a — P4: on/off intensity keywords
# ---------------------------------------------------------------------------


def test_on_off_intensity_mapping():
    """'on' maps to z5, 'off' maps to z1."""
    from intervals_icu_mcp.workout_translator import _map_intensity

    assert _map_intensity("on") == "z5 pace"
    assert _map_intensity("off") == "z1 pace"
    assert _map_intensity("On") == "z5 pace"
    assert _map_intensity("OFF") == "z1 pace"


def test_on_off_workout_translation():
    """'4-6 x 30s on / 2 mins off' → 5x, 30s z5, 2m z1."""
    description = "- 4-6 x 30s on / 2 mins off"
    result = translate_workout(description, duration_seconds=4800)
    lines = result.strip().splitlines()
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    assert lines[nx_idx] == "5x"
    assert lines[nx_idx + 1] == "- 30s z5 pace", f"Expected z5 work, got: {lines[nx_idx + 1]}"
    assert lines[nx_idx + 2] == "- 2m z1 pace", f"Expected z1 recovery, got: {lines[nx_idx + 2]}"


# ---------------------------------------------------------------------------
# Phase 5a — P1: meters vs. minutes disambiguation
# ---------------------------------------------------------------------------


def test_meter_detection_no_absurd_duration():
    """'200m@HMP' must NOT produce a 200-minute duration — falls to simple fallback."""
    description = "- 4 x 200m@HMP with 200m jog rest"
    result = translate_workout(description, duration_seconds=2400)
    # Result must not contain multi-hour absurdities like "3h20m"
    assert "3h" not in result, f"Meter misparse not caught: {result}"
    assert "200m" not in result or "pace" in result  # either cleaned up or left as fallback


def test_meter_detection_cutdown():
    """Distance-based cutdown (1600m, 1200m …) falls back to simple rather than multi-hour nonsense."""
    description = (
        "- 1600m@Tempo->10k\n"
        "- 1200m@10k\n"
        "- 800m@5k\n"
        "- 400m@3k"
    )
    result = translate_workout(description, duration_seconds=3600)
    # Must not contain anything like "26h40m" from 1600m → 1600 min
    assert "h40m" not in result, f"Meter misparse: {result}"
    assert "20h" not in result, f"Meter misparse: {result}"


def test_is_meters_not_minutes():
    """Unit test for the _is_meters_not_minutes helper."""
    from intervals_icu_mcp.workout_translator import _is_meters_not_minutes

    assert _is_meters_not_minutes(200) is True
    assert _is_meters_not_minutes(400) is True
    assert _is_meters_not_minutes(800) is True
    assert _is_meters_not_minutes(1600) is True
    assert _is_meters_not_minutes(5000) is True
    assert _is_meters_not_minutes(91) is True   # > threshold
    assert _is_meters_not_minutes(30) is False  # valid minutes
    assert _is_meters_not_minutes(45) is False
    assert _is_meters_not_minutes(60) is False
    assert _is_meters_not_minutes(90) is False  # exactly at threshold boundary — still ok as min


# ---------------------------------------------------------------------------
# Phase 5a — P2: commentary-bullet filter
# ---------------------------------------------------------------------------


def test_commentary_bullets_filtered():
    """Coaching-cue bullets are dropped; only workout steps survive."""
    description = (
        "- Total Time: 2:30-2:45\n"
        "- Hitting total time is first priority\n"
        "- 45 mins easy\n"
        "- 2 x 40mins@MP with 10 mins easy rest in between\n"
        "- 15-30 mins easy\n"
        "- If you are feeling good, add 15 more minutes"
    )
    result = translate_workout(description, duration_seconds=9000)
    lines = result.strip().splitlines()
    # "Total Time" and "Hitting..." and "If..." bullets should NOT appear as steps
    assert not any("2m45s" in l for l in lines), f"Commentary bled into steps: {result}"
    # Core workout should still be there
    assert lines[0] == "- 45m z2 pace", f"Expected warmup, got: {lines[0]}"
    nx_idx = next(i for i, l in enumerate(lines) if re.fullmatch(r"\d+x", l.strip()))
    assert lines[nx_idx] == "2x"
    assert lines[nx_idx + 1] == "- 40m z3 pace"


def test_commentary_bullet_helper():
    """Unit test for _is_commentary_bullet."""
    from intervals_icu_mcp.workout_translator import _is_commentary_bullet

    assert _is_commentary_bullet("Total Time: 2:30") is True
    assert _is_commentary_bullet("If you are feeling good, add more") is True
    assert _is_commentary_bullet("Priority is the weekend workout") is True
    assert _is_commentary_bullet("Start slower than you think") is True
    assert _is_commentary_bullet("Hitting total time is first priority") is True
    assert _is_commentary_bullet("only do 2:45 if feeling good") is True
    assert _is_commentary_bullet("45 mins easy") is False
    assert _is_commentary_bullet("2 x 40mins@MP with 10 mins rest") is False


# ---------------------------------------------------------------------------
# Phase 5a — P3: non-bullet multi-segment plain descriptions
# ---------------------------------------------------------------------------


def test_plain_segments_last_workout():
    """'Last Workout!' style: three plain-text lines, no bullets → parsed as segments."""
    description = (
        "45 mins easy to moderate\n"
        "30mins at goal marathon pace\n"
        "15 mins cool down\n"
        "\n"
        "If feeling tired, shorten even more!"
    )
    result = translate_workout(description, duration_seconds=5400)
    lines = result.strip().splitlines()
    assert lines[0] == "- 45m z2 pace", f"Got: {lines[0]}"
    assert lines[1] == "- 30m z3 pace", f"Got: {lines[1]}"
    assert lines[2] == "- 15m z2 pace", f"Got: {lines[2]}"
    assert len(lines) == 3


def test_plain_segments_requires_two_lines():
    """A single plain line does NOT activate the plain-segments parser."""
    result = translate_workout("45 mins easy", duration_seconds=2700)
    # Should be handled by _build_simple, not plain_segments
    assert result == "- 45m z2 pace"


def test_plain_segments_skips_commentary_lines():
    """Commentary lines among plain segments are silently skipped."""
    description = (
        "45 mins easy\n"
        "If feeling tired, cut this short\n"
        "15 mins cool down"
    )
    result = translate_workout(description, duration_seconds=3600)
    lines = result.strip().splitlines()
    assert lines[0] == "- 45m z2 pace"
    assert lines[1] == "- 15m z2 pace"
    assert len(lines) == 2
