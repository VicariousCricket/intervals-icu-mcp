"""Local LLM fallback for workout translation (Phase 5b).

Uses ollama as the default runtime — no GPU required, runs a background
``ollama serve`` process.  Falls back gracefully when unavailable.

Recommended setup
-----------------
1. Install ollama: https://ollama.com/download
2. Pull a model::

       ollama pull phi3:mini          # ~2.2 GB — best size/quality
       # or: ollama pull llama3.2:3b  # ~2.0 GB — strong instruction following
       # or: ollama pull mistral:7b-instruct  # ~4.1 GB — most robust

3. Ollama starts automatically on first use (or run ``ollama serve`` manually).

The LLM is only invoked when the deterministic regex pipeline raises
``WorkoutTranslationError`` (e.g. distance-based intervals with no parseable
minute duration).  Most workouts are handled without it.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_OLLAMA_BASE_URL = "http://localhost:11434"
# Preferred model — override by setting INTERVALS_ICU_LLM_MODEL env var.
_DEFAULT_MODEL = "phi3:mini"
_AVAILABILITY_TIMEOUT = 1   # seconds for the ping (keep short — checked per-workout)
_GENERATION_TIMEOUT = 60    # seconds for a full generation


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------


def _llm_available(model: str = _DEFAULT_MODEL) -> bool:
    """Return True if ollama is running and *model* is available locally."""
    try:
        with urllib.request.urlopen(
            f"{_OLLAMA_BASE_URL}/api/tags", timeout=_AVAILABILITY_TIMEOUT
        ) as resp:
            data = json.loads(resp.read().decode())
            available_models: list[str] = [m["name"] for m in data.get("models", [])]
            # Accept both "phi3:mini" and "phi3:mini-4k" style names
            base = model.split(":")[0]
            return any(m.startswith(base) for m in available_models)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a workout translator. Convert FinalSurge workout descriptions to \
Intervals.icu plain-text format.

Format rules:
- Steps start with "- " (dash space)
- Duration: 30m, 15s, 1h, 1m30s  (m = minutes, s = seconds — NOT meters/miles)
- Intensity: z1–z5 pace  (z1=recovery, z2=easy, z3=tempo/MP, z4=threshold/HMP, z5=hard/strides/on)
- Repeat blocks: a standalone "Nx" line followed by the steps; blank lines before and after the block
- Always replace N with the actual integer rep count from the description (e.g. "8 x" → 8x, "6-8x" → 7x)
- No nested repeats — flatten all intervals to one level
- Distance-based intervals (200m, 800m, 1600m etc.): estimate each step duration \
from total workout time divided by (reps × 2) for work, remainder for recovery
- "on"/"off" → z5/z1 pace respectively
- Use the exact durations written in the description. Do not calculate, scale, or \
proportionally adjust durations that are already specified in minutes or seconds.

Output constraints — your entire response must consist ONLY of lines matching one of:
  • "- <duration> <intensity>" (a workout step)
  • "<integer>x" (a repeat count, e.g. 8x)
  • a blank line (used as separator around repeat blocks)
Do not output prose, alternatives, descriptions, markdown, code fences, bullet \
symbols other than "- ", or any other text whatsoever.
Do not use markdown. Do not use backtick code fences. Do not use any formatting \
markup. Raw text only."""

# Few-shot examples as (user_turn, assistant_turn) pairs.
# Using chat turns means the model sees these as completed exchanges, not a
# pattern to "continue" — which prevents it from generating "Example N+1" hallucinations.
# Rep counts are non-trivial integers (7x, 8x, 10x) to reinforce "replace N with actual count".
_FEW_SHOT: list[tuple[str, str]] = [
    (
        "Duration: 45m\nDescription: Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )",
        "- 18m z2 pace\n\n7x\n- 17s z5 pace\n- 1m45s z2 pace",
    ),
    (
        "Duration: 1h20m\nDescription: 8 x 4:00mins @MP->HMP and 2:00mins easy",
        "- 32m z2 pace\n\n8x\n- 4m z4 pace\n- 2m z2 pace",
    ),
    (
        "Duration: 1h\nDescription: 8 x 600m@Tempo (200m jog rest)",
        "- 16m z2 pace\n\n8x\n- 3m z3 pace\n- 1m30s z1 pace",
    ),
    (
        "Duration: 50m\nDescription: 10 x 400m @ 5K effort (90s recovery jog)",
        "- 12m z2 pace\n\n10x\n- 1m30s z5 pace\n- 1m30s z1 pace",
    ),
    (
        "Duration: 1h30m\nDescription: 45 mins easy to moderate\n30mins at goal marathon pace: 8:40-9:00\n15 mins cool down\n\nIf feeling tired, shorten even more!",
        "- 45m z2 pace\n- 30m z3 pace\n- 15m z2 pace",
    ),
]


def _build_messages(description: str, duration_seconds: int) -> list[dict[str, str]]:
    """Build the /api/chat messages list with system prompt, few-shot pairs, and live query."""
    from .workout_translator import _seconds_to_icu

    messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for user_turn, assistant_turn in _FEW_SHOT:
        messages.append({"role": "user", "content": user_turn})
        messages.append({"role": "assistant", "content": assistant_turn})
    total_dur = _seconds_to_icu(duration_seconds)
    messages.append({"role": "user", "content": f"Duration: {total_dur}\nDescription: {description}"})
    return messages


# ---------------------------------------------------------------------------
# Warmup
# ---------------------------------------------------------------------------

_warmed_up: bool = False


def _warmup_llm(model: str = _DEFAULT_MODEL) -> None:
    """Send a trivial request to eliminate cold-start latency on first real use.

    Sets the module-level ``_warmed_up`` flag on success so this is only done once
    per process.  Silently ignores any errors — warmup is best-effort.
    """
    import os

    global _warmed_up
    if _warmed_up:
        return
    resolved_model = os.environ.get("INTERVALS_ICU_LLM_MODEL", model)
    payload = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": "Reply OK."},
            {"role": "user", "content": "ping"},
        ],
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 5},
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_OLLAMA_BASE_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as _:
            pass
        _warmed_up = True
        logger.debug("LLM warmup complete (model=%s).", resolved_model)
    except Exception as exc:
        logger.debug("LLM warmup failed (ignored): %s", exc)


# ---------------------------------------------------------------------------
# Translation
# ---------------------------------------------------------------------------


def _translate_with_llm(
    description: str,
    duration_seconds: int,
    sport_type: str = "Run",
    model: str = _DEFAULT_MODEL,
) -> str:
    """Translate a workout description using a local LLM via ollama.

    Args:
        description: Natural language workout description.
        duration_seconds: Total workout duration in seconds.
        sport_type: Sport type hint (passed in prompt context for future use).
        model: Ollama model name (default: ``phi3:mini``).

    Returns:
        Intervals.icu formatted workout string.

    Raises:
        RuntimeError: If ollama is unavailable or returns an error.
    """
    import os

    resolved_model = os.environ.get("INTERVALS_ICU_LLM_MODEL", model)
    _warmup_llm(model)
    messages = _build_messages(description, duration_seconds)

    payload = {
        "model": resolved_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,   # Low temp for deterministic structured output
            "num_predict": 300,   # Workouts are short; cap token spend
        },
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{_OLLAMA_BASE_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=_GENERATION_TIMEOUT) as resp:
            result = json.loads(resp.read().decode())
            response_text = result.get("message", {}).get("content", "").strip()
            if not response_text:
                raise RuntimeError("LLM returned an empty response.")
            logger.info("LLM translation succeeded (model=%s).", resolved_model)
            return response_text
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach ollama at {_OLLAMA_BASE_URL}: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"LLM generation failed: {exc}") from exc
