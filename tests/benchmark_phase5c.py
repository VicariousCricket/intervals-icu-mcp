"""Phase 5c benchmark: regex+LLM hybrid vs. straight-to-LLM.

Runs the 10 benchmark workouts from the design doc against both pipelines,
measures wall-clock time, and prints a scored comparison table for manual review.

Usage:
    uv run python tests/benchmark_phase5c.py
    uv run python tests/benchmark_phase5c.py --llm-only   # skip regex
    uv run python tests/benchmark_phase5c.py --model mistral:7b-instruct
"""

from __future__ import annotations

import argparse
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path

# Ensure src/ is importable when run from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from intervals_icu_mcp.workout_translator import _build_simple, translate_workout
from intervals_icu_mcp.workout_translator_llm import (
    _DEFAULT_MODEL,
    _llm_available,
    _translate_with_llm,
)

# ---------------------------------------------------------------------------
# Benchmark corpus
# ---------------------------------------------------------------------------
# 10 workouts immediately preceding the 2026-02-01 half marathon.
# pre_phase5: output from the post-Phase-4 translator (before this PR).
# key_fix:    which Phase-5a bug this case exercises.

@dataclass
class Case:
    date: str
    name: str
    description: str
    duration_seconds: int
    key_fix: str
    pre_phase5: str        # known (broken) output before Phase 5
    expected: str = ""     # ideal expected output (where deterministic)
    notes: str = ""

CASES: list[Case] = [
    Case(
        date="2026-01-06",
        name="Easy Run w/Strides (40 min)",
        description="4 x 100m strides with full rest (or 15-20s pickups)",
        duration_seconds=2400,
        key_fix="strides template (already passing)",
        pre_phase5="- 30m z2 pace\n\n5x\n- 15s z5 pace\n- 1m45s z1 pace",
        expected="- 30m z2 pace\n\n5x\n- 15s z5 pace\n- 1m45s z1 pace",
        notes="Pre-existing pass; strides template should still fire",
    ),
    Case(
        date="2026-01-08",
        name="Tempo + Pickups (80 min)",
        description=(
            "- 3-5 miles@HMP\n"
            "- take full rest\n"
            "- 4-6 x 30s on / 2 mins off"
        ),
        duration_seconds=4800,
        key_fix="P4 on/off + P1 miles (no unit match)",
        pre_phase5="5x\n- 30s z2 pace\n- 2m z2 pace",
        expected="5x\n- 30s z5 pace\n- 2m z1 pace",
        notes="P4: on->z5, off->z1. miles not parsed (m(?!i)), so HMP bullet dropped.",
    ),
    Case(
        date="2026-01-10",
        name="Long Run with Pickups (140 min)",
        description=(
            "10-12 x 30s on and 2 mins off easy jog\n\n"
            "- 30 mins easy \n"
            "- 60 mins easy-> moderate\n"
            "- 30 mins of workout (30s on / 2 off)\n"
            "- 10-20mins easy cool down"
        ),
        duration_seconds=8400,
        key_fix="P4 on/off (header line not parsed -- partial)",
        pre_phase5=(
            "- 30m z2 pace\n"
            "- 1h z2 pace\n"
            "- 30m z2 pace\n"
            "- 15m z2 pace"
        ),
        expected=(
            "- 30m z2 pace\n"
            "- 1h z2 pace\n"
            "- 30m z2 pace\n"
            "- 15m z2 pace"
        ),
        notes=(
            "Bullet structure preserved; header 'on/off' pattern is not parsed "
            "(the regex pipeline skips non-bullet header lines). LLM should handle this better."
        ),
    ),
    Case(
        date="2026-01-13",
        name="600s (70 min)",
        description=(
            "- 8 x 600m@Tempo 8:20-30ish pace or 3:07-10 (200m jog rest)\n"
            "- If you don't have access to a track, swap to 3 mins on / 1 off\n\n"
            "Priority is the weekend workout, so listen to your body and don't be afraid "
            "to shorten the workout or go slower if needed."
        ),
        duration_seconds=4200,
        key_fix="P1 meters (600m) + P2 commentary",
        pre_phase5="8x\n- 8m20s z3 pace\n\n- 3m z2 pace",
        expected="8x\n- 3m z3 pace\n- 1m z1 pace",
        notes=(
            "P1: 600m triggers WorkoutTranslationError -> LLM or simple fallback. "
            "P2 would have filtered 'If...' bullet but P1 fires first."
        ),
    ),
    Case(
        date="2026-01-14",
        name="Easy Run w/4-6 strides (30 min) --no description",
        description="",
        duration_seconds=1800,
        key_fix="no description (fallback --no fix needed)",
        pre_phase5="- 30m z2 pace",
        expected="- 30m z2 pace",
        notes="Empty description; simple fallback. P5 design notes this as P5 (name-based strides).",
    ),
    Case(
        date="2026-01-16",
        name="Easy Run w/Strides (40 min)",
        description="4 x 100m strides with full rest (or 15-20s pickups)",
        duration_seconds=2400,
        key_fix="strides template (already passing)",
        pre_phase5="- 30m z2 pace\n\n5x\n- 15s z5 pace\n- 1m45s z1 pace",
        expected="- 30m z2 pace\n\n5x\n- 15s z5 pace\n- 1m45s z1 pace",
        notes="Identical to 2026-01-06.",
    ),
    Case(
        date="2026-01-17",
        name="Last Big Workout! (150 min)",
        description=(
            "Total Time: 2:30-2:45\n"
            "- Hitting total time is first priority, but only do 2:45 if you are feeling good\n"
            "- Practice this like race day, and start slower than you think you need to :)\n\n"
            "Workout:\n"
            "- 45 mins easy\n"
            "- 2 x 40mins@MP(8:40-55) with 10 mins easy rest in between\n"
            "- 15-30 mins easy"
        ),
        duration_seconds=9000,
        key_fix="P2 commentary-bullet bleed",
        pre_phase5="- 2m45s z2 pace\n- 45m z2 pace\n\n2x\n- 40m z3 pace\n- 10m z1 pace\n\n- 22m30s z2 pace",
        expected="- 45m z2 pace\n\n2x\n- 40m z3 pace\n- 10m z1 pace\n\n- 22m30s z2 pace",
        notes="P2 drops 'Hitting...' and 'Practice...' bullets. '2:45' spurious step removed.",
    ),
    Case(
        date="2026-01-20",
        name="Cutdown (60 min)",
        description=(
            "4400k Cutdown - 2mins rest all\n"
            "- 1600m@Tempo->10k (8:30? who knows after the last big workout lol)\n"
            "- 1200m@10k ~5:40-50 or 1:53ish per 400m\n"
            "- 800m@5k ~3:40-50 or 1:50ish per 400m\n"
            "- 400m@3k ~1:40\n"
            "- 2 x 200m@Mile, 48-52s"
        ),
        duration_seconds=3600,
        key_fix="P1 meters (1600m, 1200m, 800m, 400m, 200m)",
        pre_phase5="- 26h40m z3 pace\n- 5m40s z2 pace\n- 3m40s z2 pace\n- 1m40s z2 pace\n\n2x\n- 50s z2 pace",
        expected="- 1h z3 pace",
        notes=(
            "P1: every bullet triggers WorkoutTranslationError -> LLM or simple fallback. "
            "Simple fallback: total 60m at dominant intensity (tempo->z3). "
            "LLM should produce structured rep-by-rep output."
        ),
    ),
    Case(
        date="2026-01-23",
        name="Easy Run with Strides (25 min)",
        description="Run 4-6 x 100m or 15-20s pickups, with full recovery",
        duration_seconds=1500,
        key_fix="strides template (already passing)",
        pre_phase5="- 15m z2 pace\n\n5x\n- 15s z5 pace\n- 1m45s z1 pace",
        expected="- 15m z2 pace\n\n5x\n- 15s z5 pace\n- 1m45s z1 pace",
        notes="Strides template: 25 min - 10 min intervals = 15 min base run.",
    ),
    Case(
        date="2026-01-24",
        name="Last Workout! (90 min)",
        description=(
            "45 mins easy to moderate\n"
            "30mins at goal marathon pace: 8:40-9:00\n"
            "15 mins cool down\n\n"
            "If feeling tired, shorten even more! Cutdown the 45mins to 30"
        ),
        duration_seconds=5400,
        key_fix="P3 plain-segment descriptions",
        pre_phase5="- 1h30m z3 pace",
        expected="- 45m z2 pace\n- 30m z3 pace\n- 15m z2 pace",
        notes=(
            "P3: plain_segments parser fires on three duration lines. "
            "'If feeling tired...' filtered by _is_commentary_bullet. "
            "Pace annotation '8:40-9:00' doesn't affect '30mins' thanks to prefer-earliest fix."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _indent(text: str, prefix: str = "    ") -> str:
    return textwrap.indent(text, prefix)

def _score_label(output: str, expected: str, pre: str) -> str:
    """Return a quick quality label comparing output to expected and pre-phase5."""
    if not expected:
        return "?"          # no ground truth defined
    if output.strip() == expected.strip():
        return "[PASS] 1.0"
    # Partial credit: key lines correct
    exp_lines = set(expected.strip().splitlines())
    out_lines = set(output.strip().splitlines())
    overlap = len(exp_lines & out_lines)
    frac = overlap / max(len(exp_lines), 1)
    if frac >= 0.75:
        return f"[PART] 0.5  ({int(frac*100)}% lines match)"
    # Better than pre-Phase 5?
    if output.strip() != pre.strip():
        return f"[FAIL] 0.0  (changed from pre; check manually)"
    return "[FAIL] 0.0  (unchanged from pre-Phase-5)"

# ---------------------------------------------------------------------------
# Runners
# ---------------------------------------------------------------------------

def run_regex(case: Case) -> tuple[str, float]:
    """Run translate_workout() and return (output, elapsed_seconds)."""
    if not case.description:
        return _build_simple(case.description or "easy", case.duration_seconds, "Run"), 0.0
    t0 = time.perf_counter()
    result = translate_workout(case.description, case.duration_seconds, "Run")
    return result, time.perf_counter() - t0


def run_llm(case: Case, model: str) -> tuple[str, float]:
    """Run _translate_with_llm() directly and return (output, elapsed_seconds)."""
    if not case.description:
        return _build_simple(case.description or "easy", case.duration_seconds, "Run"), 0.0
    t0 = time.perf_counter()
    result = _translate_with_llm(case.description, case.duration_seconds, model=model)
    return result, time.perf_counter() - t0

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    results_regex: list[tuple[str, float]],
    results_llm: list[tuple[str, float]] | None,
    model: str,
) -> None:
    hr = "-" * 80
    print(f"\n{'=' * 80}")
    print("  PHASE 5c BENCHMARK  --  regex+LLM hybrid  vs.  straight-to-LLM  ")
    print(f"  LLM model: {model}   |   Cases: {len(CASES)}")
    print(f"{'=' * 80}\n")

    total_regex = 0.0
    total_llm = 0.0
    regex_scores: list[str] = []
    llm_scores: list[str] = []

    for i, case in enumerate(CASES):
        regex_out, regex_t = results_regex[i]
        print(f"{hr}")
        print(f"  [{i+1:02d}] {case.date}  |  {case.name}")
        print(f"       Key fix: {case.key_fix}")
        if case.notes:
            print(f"       Note:    {case.notes}")
        print()

        print(f"  PRE-PHASE-5 output:")
        print(_indent(case.pre_phase5))
        print()

        rscore = _score_label(regex_out, case.expected, case.pre_phase5)
        regex_scores.append(rscore)
        total_regex += regex_t
        print(f"  REGEX PIPELINE  [{regex_t*1000:.1f} ms]  score: {rscore}")
        print(_indent(regex_out))

        if results_llm is not None:
            llm_out, llm_t = results_llm[i]
            lscore = _score_label(llm_out, case.expected, case.pre_phase5)
            llm_scores.append(lscore)
            total_llm += llm_t
            print()
            print(f"  STRAIGHT-TO-LLM  [{llm_t:.2f} s]  score: {lscore}")
            print(_indent(llm_out))

        if case.expected:
            print()
            print(f"  EXPECTED:")
            print(_indent(case.expected))

        print()

    print(f"{'=' * 80}")
    print("  SUMMARY")
    print(f"{'=' * 80}")
    print(f"  Regex pipeline  -- total: {total_regex*1000:.1f} ms  "
          f"({total_regex/len(CASES)*1000:.1f} ms/workout)")
    if results_llm is not None:
        print(f"  Straight-to-LLM -- total: {total_llm:.2f} s  "
              f"({total_llm/len(CASES):.2f} s/workout)")
        print()
        week_regex  = total_regex  / len(CASES) * 10  # 10-workout week
        week_llm    = total_llm    / len(CASES) * 10
        print(f"  Projected 10-workout week sync time:")
        print(f"    regex pipeline:  {week_regex*1000:.0f} ms")
        print(f"    straight-to-LLM: {week_llm:.1f} s")
    else:
        print(f"  (LLM not available --run `ollama pull {model}` to enable LLM comparison)")

    print()
    print("  Per-case scores (regex):")
    for i, (case, score) in enumerate(zip(CASES, regex_scores)):
        print(f"    [{i+1:02d}] {case.date:12s}  {score}")
    if results_llm is not None:
        print()
        print("  Per-case scores (straight-to-LLM):")
        for i, (case, score) in enumerate(zip(CASES, llm_scores)):
            print(f"    [{i+1:02d}] {case.date:12s}  {score}")

    print(f"\n{'=' * 80}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 5c benchmark")
    parser.add_argument("--llm-only", action="store_true", help="Skip regex pipeline")
    parser.add_argument("--model", default=_DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--no-llm", action="store_true", help="Force skip LLM even if available")
    args = parser.parse_args()

    model = args.model
    llm_ok = _llm_available(model) and not args.no_llm

    print(f"\nRunning Phase 5c benchmark ({len(CASES)} workouts)")
    print(f"LLM ({model}): {'available [ok]' if llm_ok else 'not available -- regex-only run'}")

    # Regex pipeline
    results_regex: list[tuple[str, float]] = []
    if not args.llm_only:
        print("\n>> Running regex+LLM hybrid pipeline...")
        for case in CASES:
            out, t = run_regex(case)
            results_regex.append((out, t))
            print(f"  {case.date} {case.name[:30]:<30}  {t*1000:6.1f} ms")
    else:
        results_regex = [("(skipped)", 0.0)] * len(CASES)

    # LLM pipeline
    results_llm: list[tuple[str, float]] | None = None
    if llm_ok:
        results_llm = []
        print(f"\n>> Running straight-to-LLM pipeline (model={model})...")
        for case in CASES:
            if not case.description:
                results_llm.append((_build_simple("easy", case.duration_seconds, "Run"), 0.0))
                print(f"  {case.date} {case.name[:30]:<30}  (no-desc, skipped)")
                continue
            try:
                out, t = run_llm(case, model)
                results_llm.append((out, t))
                print(f"  {case.date} {case.name[:30]:<30}  {t:.2f}s")
            except Exception as exc:
                results_llm.append((f"[LLM error: {exc}]", 0.0))
                print(f"  {case.date} {case.name[:30]:<30}  ERROR: {exc}")

    print_report(results_regex, results_llm, model)


if __name__ == "__main__":
    main()
