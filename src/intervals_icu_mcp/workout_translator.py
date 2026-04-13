"""Translate FinalSurge descriptive workout text into Intervals.icu plain-text format."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intensity mapping: FinalSurge terms → Intervals.icu format
# ---------------------------------------------------------------------------

INTENSITY_MAP: dict[str, str] = {
    # Recovery-qualified phrases (must appear before shorter "easy jog" key so
    # longer-match-first sorting resolves them to z1, not z2).
    "easy jog rest": "z1 pace",
    "walk/easy jog rest": "z1 pace",
    "easy rest": "z1 pace",
    "walk rest": "z1 pace",
    # Standard intensity terms
    "easy jog": "z2 pace",
    "easy run": "z2 pace",
    "easy": "z2 pace",
    "recovery jog": "z1 pace",
    "jog rest": "z1 pace",
    "recovery": "z1 pace",
    "jog": "z2 pace",
    "walk": "z1 pace",
    "rest": "z1 pace",
    "tempo": "z3 pace",
    "threshold": "z4 pace",
    "@threshold": "z4 pace",
    "hmp": "z4 pace",
    "@hmp": "z4 pace",
    "half marathon pace": "z4 pace",
    "marathon pace": "z3 pace",
    "@mp": "z3 pace",
    "mp": "z3 pace",
    "stride": "z5 pace",
    "strides": "z5 pace",
    "pickup": "z5 pace",
    "pickups": "z5 pace",
    "pick-up": "z5 pace",
    "pick-ups": "z5 pace",
    "fast": "z5 pace",
    "sprint": "z6 pace",
    # on/off keywords (e.g. "30s on / 2 mins off")
    "on": "z5 pace",
    "off": "z1 pace",
    # Zone pass-through
    "z1": "z1 pace",
    "z2": "z2 pace",
    "z3": "z3 pace",
    "z4": "z4 pace",
    "z5": "z5 pace",
    "z6": "z6 pace",
    # Zone with dash notation
    "z1-z2": "z2 pace",
    "z2-z3": "z2 pace",
}


# ---------------------------------------------------------------------------
# Meters vs. minutes disambiguation (Phase 5a — P1)
# ---------------------------------------------------------------------------

# Common track/road distances that would never be valid minute counts.
_METER_DISTANCES: frozenset[int] = frozenset(
    {100, 150, 200, 300, 400, 600, 800, 1000, 1200, 1500, 1600, 3000, 5000}
)
# Any Xm where X > 90 is not a realistic workout-step duration in minutes.
_MINUTE_THRESHOLD = 90


def _is_meters_not_minutes(value: float) -> bool:
    """Return True if *value* almost certainly represents meters, not minutes."""
    v = int(value)
    return v in _METER_DISTANCES or v > _MINUTE_THRESHOLD


def _map_intensity(raw: str, sport_type: str = "Run") -> str:
    """Return Intervals.icu intensity string for a raw FinalSurge intensity token."""
    key = raw.strip().lower()
    if key in INTENSITY_MAP:
        return INTENSITY_MAP[key]
    # Z1-Z5 pattern with capitalisation
    zm = re.fullmatch(r"z(\d)(?:-z\d)?", key)
    if zm:
        return f"z{zm.group(1)} pace"
    return "z2 pace"  # conservative default


# ---------------------------------------------------------------------------
# Duration helpers
# ---------------------------------------------------------------------------


def _seconds_to_icu(total_seconds: int) -> str:
    """Convert a duration in seconds to Intervals.icu format (e.g. 1m30s, 45s, 10m)."""
    if total_seconds <= 0:
        return "0s"
    hours = total_seconds // 3600
    remainder = total_seconds % 3600
    minutes = remainder // 60
    seconds = remainder % 60
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return "".join(parts) if parts else "0s"


def _parse_duration_to_seconds(text: str) -> int | None:
    """Parse a duration string like '10:00', '10min', '15s', '1m30s' → seconds."""
    text = text.strip()
    # MM:SS or H:MM:SS
    colon_match = re.fullmatch(r"(?:(\d+):)?(\d+):(\d+)", text)
    if colon_match:
        h = int(colon_match.group(1) or 0)
        m = int(colon_match.group(2))
        s = int(colon_match.group(3))
        return h * 3600 + m * 60 + s
    # 1h2m30s style
    compound = re.fullmatch(
        r"(?:(\d+)h)?(?:(\d+)m(?!i))?(?:(\d+)s)?",
        text,
        re.IGNORECASE,
    )
    if compound and compound.group(0):
        h = int(compound.group(1) or 0)
        m = int(compound.group(2) or 0)
        s = int(compound.group(3) or 0)
        total = h * 3600 + m * 60 + s
        if total > 0:
            return total
    # plain number + unit
    plain = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(min|mins|minutes?|s|sec|secs|seconds?|h|hrs?|hours?)", text, re.IGNORECASE)
    if plain:
        val = float(plain.group(1))
        unit = plain.group(2).lower()
        if unit.startswith("h"):
            return int(val * 3600)
        if unit.startswith("m"):
            return int(val * 60)
        return int(val)
    # bare seconds e.g. "15" (assume seconds when small)
    bare = re.fullmatch(r"(\d+)", text)
    if bare:
        return int(bare.group(1))
    return None


def _resolve_range(low: float, high: float, strategy: str = "midpoint") -> float:
    """Resolve a numeric range to a single value."""
    if strategy == "midpoint_rounded_down":
        return float(int((low + high) / 2))
    # midpoint
    return (low + high) / 2


# ---------------------------------------------------------------------------
# Strides / pickups template
# ---------------------------------------------------------------------------

# Detects strides/pickups anywhere in description (case-insensitive whole word).
_STRIDES_RE = re.compile(r"\b(stride|strides|pickup|pick-up|pickups|pick-ups)\b", re.IGNORECASE)

# Guard: if an explicit zone or "@Stride/Fast" annotation is already present,
# the paren-form parser already handled it — don't override with the template.
_EXPLICIT_ZONE_RE = re.compile(r"\b[Zz][1-6]\b", re.IGNORECASE)

# Standard strides template: 5 reps × (15 s hard + 1 m 45 s recovery).
_STRIDES_REPS = 5
_STRIDES_WORK_SECS = 15   # 15 s @ z5
_STRIDES_REST_SECS = 105  # 1 m 45 s @ z1  (2-minute gap between strides)


def _build_strides(duration_seconds: int) -> str:
    """
    Emit the standard strides block: easy base run + 5 × (15 s z5 / 1m45s z1).

    The total interval time (5 × 2 min = 10 min) is subtracted from the total
    workout duration to size the base easy run.
    """
    interval_secs = _STRIDES_REPS * (_STRIDES_WORK_SECS + _STRIDES_REST_SECS)
    base_secs = max(0, duration_seconds - interval_secs)
    lines: list[str] = []
    if base_secs > 60:
        lines.append(f"- {_seconds_to_icu(base_secs)} z2 pace")
        lines.append("")
    lines.append(f"{_STRIDES_REPS}x")
    lines.append(f"- {_seconds_to_icu(_STRIDES_WORK_SECS)} z5 pace")
    lines.append(f"- {_seconds_to_icu(_STRIDES_REST_SECS)} z1 pace")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


class WorkoutTranslationError(Exception):
    """Raised when translation cannot proceed."""


def _extract_repeat_block(description: str) -> tuple[int, str, list[str]] | None:
    """
    Find the first "Nx(...)" or "N-Mx(...)" pattern in the description.

    Returns (reps, inner_text, remaining_tokens_outside_parens) or None.
    remaining_tokens is a list of text segments that were outside the parentheses block.
    """
    # Pattern: optional range N-M or single N followed by 'x' then '(' ... ')'
    # Allow one level of nested parens (e.g. "Fast (Z5)") inside the block.
    pattern = re.compile(
        r"(\d+)(?:-(\d+))?x\s*"
        r"(\((?:[^()]*|\([^()]*\))*\))",
        re.IGNORECASE,
    )
    m = pattern.search(description)
    if not m:
        return None
    low = float(m.group(1))
    high = float(m.group(2)) if m.group(2) else low
    reps = int(_resolve_range(low, high, "midpoint_rounded_down"))
    # Strip outer parens to get inner content
    inner = m.group(3)[1:-1]
    # Split description around the matched block
    before = description[: m.start()]
    after = description[m.end() :]
    return reps, inner, [before, after]


def _parse_inner_steps(inner: str, sport_type: str) -> list[tuple[int, str]]:
    """
    Parse the inside of a repeat block into (duration_seconds, intensity) pairs.

    Scans sequentially for all duration tokens; each token's associated intensity
    is the text between it and the next token.  This handles both:
      - slash-separated segments: ``15-20s @ Stride / Full recovery easy jog``
      - adjacent segments:        ``10:00 @ HMP (Z4) 5:00 Walk / Easy Jog``
    """
    # Normalise separators so "/" doesn't confuse duration scanning
    text = re.sub(r"[/,\n]+", " ", inner)

    # Pattern that matches (in priority order):
    #   1. range duration:  15-20s, 10-15m
    #   2. colon duration:  10:00, 5:00
    #   3. plain duration:  17s, 10m, 1h
    token_pat = re.compile(
        r"\b(\d+)\s*-\s*(\d+)\s*(s|sec|secs|seconds?|m(?!i)|min|mins|minutes?|h|hrs?)\b"
        r"|\b(\d+):(\d{2})\b"
        r"|\b(\d+(?:\.\d+)?)\s*(s|sec|secs|seconds?|m(?!i)|min|mins|minutes?|h|hrs?|hours?)\b",
        re.IGNORECASE,
    )

    matches = list(token_pat.finditer(text))
    if not matches:
        return []

    steps: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        # --- parse duration ---
        if m.group(1) and m.group(2):  # range
            low, high = float(m.group(1)), float(m.group(2))
            mid = _resolve_range(low, high, "midpoint")
            unit = m.group(3).lower()
            if unit.startswith("h"):
                dur = int(mid * 3600)
            elif unit.startswith("m"):
                # "m", "min", "mins", "minutes" all mean minutes; "miles" is already
                # excluded by the m(?!i) negative lookahead in the token pattern.
                if _is_meters_not_minutes(low) or _is_meters_not_minutes(high):
                    raise WorkoutTranslationError(
                        f"Distance-based range: {int(low)}-{int(high)}m detected."
                    )
                dur = int(mid * 60)
            else:
                dur = int(mid)
        elif m.group(4) and m.group(5):  # MM:SS
            dur = int(m.group(4)) * 60 + int(m.group(5))
        else:  # plain
            val = float(m.group(6))
            unit = m.group(7).lower()
            if unit.startswith("h"):
                dur = int(val * 3600)
            elif unit.startswith("m"):
                # "m", "min", "mins", "minutes" all mean minutes; "miles" excluded by regex.
                if _is_meters_not_minutes(val):
                    raise WorkoutTranslationError(
                        f"Distance-based step: {int(val)}m detected."
                    )
                dur = int(val * 60)
            else:
                dur = int(val)

        # --- intensity: text from end of this match to start of next ---
        intensity_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        intensity_text = text[m.end() : intensity_end].strip()
        # Zone hint in parentheses takes priority
        zone_m = re.search(r"\(\s*(Z\d(?:-Z\d)?)\s*\)", intensity_text, re.IGNORECASE)
        if zone_m:
            intensity = _map_intensity(zone_m.group(1), sport_type)
        else:
            intensity = _identify_intensity(intensity_text, sport_type)

        steps.append((dur, intensity))

    return steps


def _parse_step_fragment(fragment: str, sport_type: str) -> tuple[int | None, str]:
    """
    Extract (duration_seconds, intensity) from a single step fragment like
    '15-20s @ Stride / Fast (Z5)' or '5:00 Walk / Easy Jog recovery'.
    """
    # Normalise '@' separator
    fragment = fragment.replace("@", " ").strip()

    # Remove parenthetical zone annotations like "(Z5)" that follow intensity words
    # but keep the zone info to help mapping
    zone_in_parens = re.search(r"\(\s*(Z\d(?:-Z\d)?)\s*\)", fragment, re.IGNORECASE)
    zone_hint: str | None = zone_in_parens.group(1) if zone_in_parens else None
    fragment_clean = re.sub(r"\([^)]*\)", "", fragment).strip()

    # Duration: look for range like "15-20s" or "10-15m" or plain "15s"
    dur_range_pat = re.compile(
        r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(s|sec|secs|seconds?|m(?!i)|min|mins|minutes?|h|hrs?|hours?|:\d\d)",
        re.IGNORECASE,
    )
    dur_plain_pat = re.compile(
        r"(\d+(?:\.\d+)?)\s*(s|sec|secs|seconds?|m(?!i)|min|mins|minutes?|h|hrs?|hours?)",
        re.IGNORECASE,
    )
    colon_pat = re.compile(r"(\d+):(\d{2})")

    duration_seconds: int | None = None
    consumed_span: tuple[int, int] | None = None

    m_range = dur_range_pat.search(fragment_clean)
    m_plain = dur_plain_pat.search(fragment_clean)
    m_colon = colon_pat.search(fragment_clean)

    # Prefer the earliest-starting match so that an explicit "30mins" or "600m"
    # at position 0 is not shadowed by a pace annotation like "8:40" or a range
    # like "40-9:00" found later in the same fragment.
    if m_range and m_plain and m_plain.start() <= m_range.start():
        m_range = None
    if m_range and m_colon and m_colon.start() <= m_range.start():
        m_range = None
    if m_colon and m_plain and m_plain.start() < m_colon.start():
        m_colon = None

    if m_range:
        low = float(m_range.group(1))
        high = float(m_range.group(2))
        mid = _resolve_range(low, high, "midpoint")
        unit = m_range.group(3).lower()
        if unit.startswith("h"):
            duration_seconds = int(mid * 3600)
        elif unit.startswith(":"):
            duration_seconds = int(mid * 60)
        elif unit.startswith("m"):
            # "m", "min", "mins", "minutes" all mean minutes; "miles" excluded by regex.
            if _is_meters_not_minutes(low) or _is_meters_not_minutes(high):
                raise WorkoutTranslationError(
                    f"Distance-based range: {int(low)}-{int(high)}m detected."
                )
            duration_seconds = int(mid * 60)
        else:
            duration_seconds = int(mid)
        consumed_span = (m_range.start(), m_range.end())
    elif m_colon:
        duration_seconds = int(m_colon.group(1)) * 60 + int(m_colon.group(2))
        consumed_span = (m_colon.start(), m_colon.end())
    elif m_plain:
        val = float(m_plain.group(1))
        unit = m_plain.group(2).lower()
        if unit.startswith("h"):
            duration_seconds = int(val * 3600)
        elif unit.startswith("m"):
            # "m", "min", "mins", "minutes" all mean minutes; "miles" excluded by regex.
            if _is_meters_not_minutes(val):
                raise WorkoutTranslationError(
                    f"Distance-based step: {int(val)}m detected."
                )
            duration_seconds = int(val * 60)
        else:
            duration_seconds = int(val)
        consumed_span = (m_plain.start(), m_plain.end())

    # Intensity: everything that's not the duration and not digits/punctuation
    if consumed_span is not None:
        intensity_text = (
            fragment_clean[: consumed_span[0]] + " " + fragment_clean[consumed_span[1] :]
        ).strip()
    else:
        intensity_text = fragment_clean

    # Prefer explicit zone hint from parens
    if zone_hint:
        intensity = _map_intensity(zone_hint, sport_type)
    else:
        # Try to find an intensity keyword in the remaining text
        intensity = _identify_intensity(intensity_text, sport_type)

    return duration_seconds, intensity


def _identify_intensity(text: str, sport_type: str) -> str:
    """Scan text for known intensity keywords, longest match first."""
    lower = text.lower().strip()
    # Handle X->Y range notation (e.g. @MP->HMP, z3->z4): take the target (right side).
    arrow_m = re.search(r"(\w+)\s*->\s*(\w+)", lower)
    if arrow_m:
        target = arrow_m.group(2).strip()
        if target in INTENSITY_MAP:
            return INTENSITY_MAP[target]
        zm = re.fullmatch(r"z(\d)(?:-z\d)?", target)
        if zm:
            return f"z{zm.group(1)} pace"
    # Check multi-word keys first (longest first)
    for key in sorted(INTENSITY_MAP.keys(), key=len, reverse=True):
        if key in lower:
            return INTENSITY_MAP[key]
    # Zone pattern Z1-Z5
    zm = re.search(r"\bz(\d)(?:-z\d)?\b", lower, re.IGNORECASE)
    if zm:
        return f"z{zm.group(1)} pace"
    return "z2 pace"


# ---------------------------------------------------------------------------
# Inline repeat pattern: "N x work [and|with|/] recovery" (no parentheses)
# ---------------------------------------------------------------------------


def _extract_inline_repeat_block(
    description: str,
) -> tuple[int, str, str, str] | None:
    """
    Find the "N x work [and|with|/] recovery" prose pattern (no parentheses).

    Handles:
    - ``8 x 4:00mins @MP->HMP and 2:00mins easy``
    - ``- 8 x 4:00mins @MP->HMP and 2:00mins easy``  (bullet prefix)
    - ``4 x 15mins at MP with 5 mins rest``
    - ``6-8 x 800s with 400m jog rest``

    Returns ``(reps, before_text, work_text, recovery_text)`` or ``None``.
    """
    # Strip a leading bullet/dash prefix (e.g. "- 8 x …")
    desc = re.sub(r"^\s*[-*•]\s+", "", description.strip())

    # Match "N x" or "N-Mx" where x is NOT immediately followed by "("
    # (paren form is handled by _extract_repeat_block).
    # Require \b before N to avoid matching e.g. "Z5x".
    pattern = re.compile(
        r"\b(\d+)(?:-(\d+))?\s*[xX](?!\s*\()\s+",
        re.IGNORECASE,
    )
    m = pattern.search(desc)
    if not m:
        return None

    low = float(m.group(1))
    high = float(m.group(2)) if m.group(2) else low
    reps = max(1, int(_resolve_range(low, high, "midpoint_rounded_down")))

    before_text = desc[: m.start()].strip()
    rest = desc[m.end() :].strip()

    # Split on a recovery separator followed by a digit ("and 2:00", "with 5 mins")
    sep_m = re.search(r"\s+(?:and|with)\s+(?=\d)", rest, re.IGNORECASE)
    slash_m = re.search(r"\s*/\s*", rest)

    if sep_m:
        work_text = rest[: sep_m.start()].strip()
        recovery_text = rest[sep_m.end() :].strip()
    elif slash_m:
        work_text = rest[: slash_m.start()].strip()
        recovery_text = rest[slash_m.end() :].strip()
    else:
        work_text = rest
        recovery_text = ""

    return reps, before_text, work_text, recovery_text


def _build_inline_repeat(
    inline: tuple[int, str, str, str],
    duration_seconds: int,
    sport_type: str,
) -> str:
    """Build Intervals.icu format from an inline ``N x work [sep] recovery`` block."""
    reps, before_text, work_text, recovery_text = inline

    # Parse work step
    work_dur, work_intensity = _parse_step_fragment(work_text, sport_type)
    if work_dur is None:
        raise WorkoutTranslationError(
            f"Could not parse work duration from: {work_text!r}"
        )

    # Parse recovery step (duration may be absent for distance-based recoveries)
    rec_dur: int | None = None
    rec_intensity = "z2 pace"
    if recovery_text:
        rec_dur, rec_intensity = _parse_step_fragment(recovery_text, sport_type)

    # Sanity check: work × reps must fit within total duration
    if work_dur * reps > duration_seconds:
        raise WorkoutTranslationError(
            f"Work {work_dur}s × {reps} reps = {work_dur * reps}s exceeds "
            f"total {duration_seconds}s. Likely distance-based intervals."
        )

    # Time already accounted for
    work_total = work_dur * reps
    rec_total = (rec_dur or 0) * reps
    interval_total = work_total + rec_total

    # Parse any explicit warmup text before the "N x"
    before_steps = _parse_surrounding(before_text, sport_type) if before_text else []
    known_before = sum(d for d, _ in before_steps)

    remaining = duration_seconds - known_before - interval_total

    # If recovery duration could not be parsed but there is recovery text,
    # distribute the remaining time evenly across reps as recovery.
    if rec_dur is None and recovery_text and remaining > 0 and reps > 0:
        rec_dur = remaining // reps
        rec_intensity = _identify_intensity(recovery_text, sport_type)
        remaining = duration_seconds - known_before - work_total - rec_dur * reps

    lines: list[str] = []

    # Warmup / base run
    if before_steps:
        for d, i in before_steps:
            lines.append(f"- {_seconds_to_icu(d)} {i}")
    elif remaining > 60:
        base_intensity = (
            _identify_intensity(before_text, sport_type) if before_text else "z2 pace"
        )
        lines.append(f"- {_seconds_to_icu(remaining)} {base_intensity}")

    # Blank line before interval block
    if lines:
        lines.append("")

    lines.append(f"{reps}x")
    lines.append(f"- {_seconds_to_icu(work_dur)} {work_intensity}")
    if rec_dur is not None and rec_dur > 0:
        lines.append(f"- {_seconds_to_icu(rec_dur)} {rec_intensity}")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Commentary-bullet detection (Phase 5a — P2)
# ---------------------------------------------------------------------------

# Bullet lines that start with these words are coaching cues, not steps.
_COMMENTARY_RE = re.compile(
    r"^(by\s|total\s|aim\s|note[:\s]|start\s|priority\s|if\s|goal[:\s]|"
    r"cool\s+down\s+to|hitting\s|practice\s|only\s+do\s)",
    re.IGNORECASE,
)
# Lines that contain an arithmetic summary like "20 easy + 48 w/o" are also commentary.
_ARITHMETIC_RE = re.compile(r"\d+\s*\w+\s*\+\s*\d+")


def _is_commentary_bullet(content: str) -> bool:
    """Return True if a bullet/line content is a coaching cue rather than a workout step."""
    if _COMMENTARY_RE.match(content):
        return True
    if _ARITHMETIC_RE.search(content):
        return True
    return False


# ---------------------------------------------------------------------------
# Multi-line bullet-list parser
# ---------------------------------------------------------------------------


def _parse_bullet_list(description: str, sport_type: str) -> str | None:
    """
    Parse a description that consists of ≥2 bullet lines into structured steps.

    Each bullet is treated as an independent workout segment.  A bullet that
    contains an inline "N x work [sep] recovery" pattern is emitted as a repeat
    block (with surrounding blank lines); all other bullets become plain steps.

    Returns the formatted ICU string, or ``None`` if there are fewer than 2
    bullet lines in the description.
    """
    lines = description.strip().splitlines()
    bullet_lines = [l.strip() for l in lines if re.match(r"^-\s", l.strip())]

    if len(bullet_lines) < 2:
        return None

    # Each block is ("step", [line, ...]) or ("repeat", [line, ...])
    blocks: list[tuple[str, list[str]]] = []

    for bullet in bullet_lines:
        content = bullet[2:].strip()  # strip leading "- "

        # Skip coaching-cue bullets (commentary bleed — Phase 5a P2)
        if _is_commentary_bullet(content):
            continue

        # Check for an inline Nx pattern embedded in this bullet
        inline = _extract_inline_repeat_block(content)
        if inline is not None:
            reps, _before, work_text, recovery_text = inline
            work_dur, work_intensity = _parse_step_fragment(work_text, sport_type)
            if work_dur is not None and work_dur > 0:
                repeat_lines: list[str] = [
                    f"{reps}x",
                    f"- {_seconds_to_icu(work_dur)} {work_intensity}",
                ]
                if recovery_text:
                    rec_dur, rec_intensity = _parse_step_fragment(recovery_text, sport_type)
                    if rec_dur is not None and rec_dur > 0:
                        repeat_lines.append(f"- {_seconds_to_icu(rec_dur)} {rec_intensity}")
                blocks.append(("repeat", repeat_lines))
                continue

        # Plain step
        dur, intensity = _parse_step_fragment(content, sport_type)
        if dur is not None and dur > 0:
            blocks.append(("step", [f"- {_seconds_to_icu(dur)} {intensity}"]))

    if not blocks:
        return None

    # Assemble: insert blank lines before and after every repeat block
    result: list[str] = []
    for i, (block_type, block_lines) in enumerate(blocks):
        prev_type = blocks[i - 1][0] if i > 0 else None
        if i > 0 and (block_type == "repeat" or prev_type == "repeat"):
            result.append("")
        result.extend(block_lines)

    return "\n".join(result)


# ---------------------------------------------------------------------------
# Non-bullet multi-segment parser (Phase 5a — P3)
# ---------------------------------------------------------------------------


def _parse_plain_segments(description: str, sport_type: str) -> str | None:
    """
    Parse a description made of newline-separated plain lines (no "- " prefix).

    Each non-empty, non-commentary line is attempted as a workout step via
    ``_parse_step_fragment``.  Returns a formatted ICU string if ≥ 2 lines
    yield a valid duration; returns ``None`` otherwise.

    Inserted between ``_parse_bullet_list`` and ``_extract_inline_repeat_block``
    in ``_translate()`` so that multi-segment prose descriptions like::

        45 mins easy to moderate
        30mins at goal marathon pace
        15 mins cool down

    are captured without requiring dash-prefixed bullets.
    """
    lines = description.strip().splitlines()
    # Only process non-bullet, non-empty lines
    candidate_lines = [
        ln.strip()
        for ln in lines
        if ln.strip() and not re.match(r"^-\s", ln.strip())
    ]

    if len(candidate_lines) < 2:
        return None

    steps: list[tuple[int, str]] = []
    for line in candidate_lines:
        if _is_commentary_bullet(line):
            continue
        try:
            dur, intensity = _parse_step_fragment(line, sport_type)
        except WorkoutTranslationError:
            continue
        if dur is not None and dur > 0:
            steps.append((dur, intensity))

    if len(steps) < 2:
        return None

    return "\n".join(f"- {_seconds_to_icu(d)} {i}" for d, i in steps)


# ---------------------------------------------------------------------------
# High-level translation
# ---------------------------------------------------------------------------


def translate_workout(
    description: str,
    duration_seconds: int,
    sport_type: str = "Run",
) -> str:
    """
    Translate a FinalSurge descriptive workout into Intervals.icu plain-text format.

    The pipeline runs in order:
    1. Deterministic regex pipeline (Phases 1–5a).
    2. Local LLM fallback via ollama (Phase 5b) — only when the regex pipeline
       raises ``WorkoutTranslationError`` (e.g. distance-based intervals).
    3. Simple single-step fallback — when the LLM is unavailable or also fails.

    Args:
        description: Natural language workout description from FinalSurge.
        duration_seconds: Total workout duration in seconds.
        sport_type: "Run", "Ride", or "Swim".

    Returns:
        Intervals.icu formatted workout string, or a simple fallback if all
        translation attempts fail.
    """
    try:
        return _translate(description, duration_seconds, sport_type)
    except WorkoutTranslationError as exc:
        logger.info("Regex pipeline could not translate workout (%s); trying LLM fallback.", exc)
        try:
            from .workout_translator_llm import _llm_available, _translate_with_llm

            if _llm_available():
                result = _translate_with_llm(description, duration_seconds, sport_type)
                logger.info("LLM fallback succeeded.")
                return result
            logger.warning("LLM unavailable (ollama not running or model not pulled).")
        except Exception as llm_exc:  # noqa: BLE001
            logger.warning("LLM fallback failed: %s", llm_exc)
        logger.warning("Using simple fallback for: %s", description[:80])
        return _build_simple(description, duration_seconds, sport_type)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected translation error: %s. Returning original.", exc)
        return description


def _translate(description: str, duration_seconds: int, sport_type: str) -> str:
    result = _extract_repeat_block(description)

    if result is None:
        # Strides / pickups keyword → apply standard 5 × (15 s z5 / 1m45s z1) template.
        # Only fires when there is no explicit zone annotation already in the description
        # (those are handled correctly by the paren-form or inline parsers above/below).
        if (
            sport_type == "Run"
            and _STRIDES_RE.search(description)
            and not _EXPLICIT_ZONE_RE.search(description)
        ):
            return _build_strides(duration_seconds)

        # Try multi-line bullet-list first (handles pure step lists and bullets
        # that embed an Nx pattern, without being confused by surrounding prose).
        bullet_result = _parse_bullet_list(description, sport_type)
        if bullet_result is not None:
            return bullet_result

        # Phase 5a P3: non-bullet multi-segment plain descriptions
        # (e.g. "45 mins easy\n30mins at MP\n15 mins cool down")
        plain_result = _parse_plain_segments(description, sport_type)
        if plain_result is not None:
            return plain_result

        # Try the prose/bullet "N x work [sep] recovery" pattern
        inline = _extract_inline_repeat_block(description)
        if inline is not None:
            return _build_inline_repeat(inline, duration_seconds, sport_type)
        # No repeat block – simple workout
        return _build_simple(description, duration_seconds, sport_type)

    reps, inner, surrounding = result
    before_text, after_text = surrounding[0], surrounding[1]

    # Parse the interval steps
    interval_steps = _parse_inner_steps(inner, sport_type)
    if not interval_steps:
        raise WorkoutTranslationError("Could not parse any steps from repeat block.")

    # Separate work steps from recovery steps heuristically:
    # The last step in the inner block is usually the recovery.
    # If only one step, infer recovery from "full recovery" text or use 5× work duration.
    if len(interval_steps) == 1:
        work_steps = interval_steps
        # Check if description mentions recovery (no explicit duration given)
        recovery_keyword = re.search(r"\bfull\s+recovery\b|\brecovery\b|\bjog\b", inner, re.IGNORECASE)
        if recovery_keyword:
            inferred_recovery_dur = max(60, interval_steps[0][0] * 5)
            recovery_intensity = _identify_intensity(
                inner[recovery_keyword.start() :], sport_type
            )
            recovery_steps: list[tuple[int, str]] = [(inferred_recovery_dur, recovery_intensity)]
        else:
            recovery_steps = []
    else:
        work_steps = interval_steps[:-1]
        recovery_steps = [interval_steps[-1]]

    # Total time consumed by intervals
    interval_work_secs = sum(d for d, _ in work_steps) * reps
    interval_recovery_secs = sum(d for d, _ in recovery_steps) * reps
    total_interval_secs = interval_work_secs + interval_recovery_secs

    # Parse surrounding segments for base run / cooldown
    before_steps = _parse_surrounding(before_text, sport_type)
    after_steps = _parse_surrounding(after_text, sport_type)

    # Known surrounding time
    known_before_secs = sum(d for d, _ in before_steps)
    known_after_secs = sum(d for d, _ in after_steps)

    # Remaining time → assign to base run if before_text has no explicit duration
    remaining_secs = duration_seconds - total_interval_secs - known_before_secs - known_after_secs

    lines: list[str] = []

    # Build base run from before_steps or remaining time
    if before_steps:
        for dur, intensity in before_steps:
            lines.append(f"- {_seconds_to_icu(dur)} {intensity}")
    elif remaining_secs > 0 and not after_steps:
        # All remaining time before intervals
        base_intensity = _identify_intensity(before_text, sport_type)
        lines.append(f"- {_seconds_to_icu(remaining_secs)} {base_intensity}")
    elif remaining_secs > 0:
        # Split remaining: half before, half after as cooldown
        half = remaining_secs // 2
        base_intensity = _identify_intensity(before_text, sport_type)
        if half > 0:
            lines.append(f"- {_seconds_to_icu(half)} {base_intensity}")

    # Interval block (blank line before)
    if lines:
        lines.append("")
    lines.append(f"{reps}x")
    for dur, intensity in work_steps:
        lines.append(f"- {_seconds_to_icu(dur)} {intensity}")
    for dur, intensity in recovery_steps:
        lines.append(f"- {_seconds_to_icu(dur)} {intensity}")

    # After steps (cooldown)
    if after_steps:
        lines.append("")
        for dur, intensity in after_steps:
            lines.append(f"- {_seconds_to_icu(dur)} {intensity}")
    elif remaining_secs > 0 and known_before_secs == 0 and not before_steps:
        # Already handled above (no explicit after either)
        pass
    elif remaining_secs > 0:
        # Put remaining as cooldown
        half = remaining_secs - (remaining_secs // 2)
        cool_intensity = _identify_intensity(after_text, sport_type) if after_text.strip() else "z2 pace"
        if half > 0:
            lines.append("")
            lines.append(f"- {_seconds_to_icu(half)} {cool_intensity}")

    return "\n".join(lines).strip()


def _parse_surrounding(text: str, sport_type: str) -> list[tuple[int, str]]:
    """
    Parse text outside a repeat block into a list of (duration_seconds, intensity) steps.

    Splits on sentence boundaries / multiple durations if present.
    """
    text = text.strip()
    if not text:
        return []

    steps: list[tuple[int, str]] = []

    # Look for explicit "MM:SS" or "Xm" tokens followed by intensity
    segment_pat = re.compile(
        r"(\d+:\d{2}|\d+(?:\.\d+)?\s*(?:min|mins|minutes?|s|sec|secs|h|hrs?)\b)",
        re.IGNORECASE,
    )
    segments = list(segment_pat.finditer(text))

    if not segments:
        return []

    for i, seg in enumerate(segments):
        dur = _parse_duration_to_seconds(seg.group(0))
        if dur is None:
            continue
        # Intensity: text between this segment and the next (or end)
        start = seg.end()
        end = segments[i + 1].start() if i + 1 < len(segments) else len(text)
        intensity_text = text[start:end]
        intensity = _identify_intensity(intensity_text, sport_type)
        steps.append((dur, intensity))

    return steps


def _build_simple(description: str, duration_seconds: int, sport_type: str) -> str:
    """Build a single-step workout when there's no repeat block."""
    intensity = _identify_intensity(description, sport_type)
    return f"- {_seconds_to_icu(duration_seconds)} {intensity}"
