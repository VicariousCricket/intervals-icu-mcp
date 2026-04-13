# Workout Translation Function Design
## FinalSurge → Intervals.icu Structured Format

### Problem Statement
Coach workouts in FinalSurge are often descriptive/natural language rather than strictly structured. Need automated translation to Intervals.icu's strict plain-text workout format.

### Example Transformation

**Input** (FinalSurge):
```
Name: Easy Run with Strides
Duration: 45 minutes
Description: "Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )"
```

**Output** (Intervals.icu format):
```
- 18m z2 pace

6x
- 15s z5 pace
- 1m45s z2 pace
```

### Intervals.icu Format Rules (from documentation)

#### Core Syntax
```
- [duration/distance] [intensity] [optional_cadence]
```

#### Duration formats
- Hours: `1h`
- Minutes: `10m`, `5m`
- Seconds: `30s`, `90s`
- Combined: `1m30s`, `1h2m30s`
- Shorthand: `5'`, `30"`, `1'30"`

#### Intensity formats (Running)
- Zones: `z1 pace`, `z2 pace`, `z3 pace`, `z4 pace`, `z5 pace`
- Percentages: `78-82% pace`, `90% pace`
- Heart rate: `70% HR`, `75-80% HR`, `Z2 HR`

#### Repeat syntax
Two valid forms:
1. Header style: `Main Set 6x`
2. Standalone: `6x` (on its own line before the repeated block)

#### Critical formatting rules
- Steps start with `-` (dash + space)
- Blank lines surround interval blocks (before and after `Nx` repeats)
- **Nested repeats NOT supported** - intervals must be flat
- Section headers: lines without `-`
- Free text allowed anywhere; text before first duration/intensity becomes the step cue

### Workflow Integration Points

#### Option 1: Pre-processing in MCP Server (RECOMMENDED)
```
FinalSurge API → parse_workout() → translate_workout() → create_event() → Intervals.icu API
```

**Location**: New function in MCP server
**Function signature**:
```python
def translate_workout(
    description: str,
    duration_seconds: int,
    sport_type: str = "Run"
) -> str:
    """
    Translate FinalSurge descriptive workout into Intervals.icu format.

    Args:
        description: Natural language workout description from FinalSurge
        duration_seconds: Total workout duration in seconds
        sport_type: "Run", "Ride", or "Swim"

    Returns:
        Intervals.icu formatted workout string
    """
```

**Advantages**:
- Single source of truth for translation logic
- Reusable across bulk/single create operations
- Can be tested independently
- Doesn't require Claude for every workout

#### Option 2: Claude-assisted translation
```
FinalSurge API → MCP → Claude (translate) → MCP (create) → Intervals.icu API
```

**Advantages**:
- Handles complex/ambiguous descriptions better
- Can learn from corrections
- More flexible with varied formats

**Disadvantages**:
- Requires API call per workout
- Latency
- Token costs

### Translation Logic Design

#### 1. Parsing strategy
```python
class WorkoutParser:
    def parse(self, description: str, duration_seconds: int):
        """Extract workout components"""
        # Identify intervals pattern: "Nx(...)" or "N-Mx(...)"
        intervals = self.extract_intervals(description)

        # Identify intensity markers: "Z1-Z5", "@HMP", "@threshold", "easy", "fast"
        intensities = self.extract_intensities(description)

        # Identify duration markers: "15-20s", "10min", etc.
        durations = self.extract_durations(description)

        # Calculate remaining time (total - intervals = base run)
        base_duration = self.calculate_base(duration_seconds, intervals, durations)

        return WorkoutComponents(intervals, intensities, durations, base_duration)
```

#### 2. Range resolution rules
```python
RANGE_RESOLUTION_RULES = {
    "reps": {
        "strategy": "midpoint_rounded_down",
        # "6-8x" → 7x (round down from 7.0)
        # "4-6x" → 5x
    },
    "duration": {
        "strategy": "midpoint",
        # "15-20s" → 17s (average)
        # "10-15m" → 12m30s
    },
    "recovery": {
        "strategy": "calculated",
        # "Full recovery" → calculate from: (total_time - work_time) / reps
    }
}
```

#### 3. Intensity mapping
```python
INTENSITY_MAP = {
    # FinalSurge terms → Intervals.icu format
    "easy": "z2 pace",
    "recovery": "z1 pace",
    "easy jog": "z2 pace",
    "hmp": "z4 pace",  # Half marathon pace
    "threshold": "z4 pace",
    "tempo": "z3 pace",
    "stride": "z5 pace",
    "fast": "z5 pace",
    "sprint": "z6 pace",
    "on": "z5 pace",   # "30s on" → hard effort
    "off": "z1 pace",  # "2 mins off" → recovery

    # Zone notation (already matches)
    "z1": "z1 pace",
    "z2": "z2 pace",
    "z3": "z3 pace",
    "z4": "z4 pace",
    "z5": "z5 pace",
}
```

#### 4. Structure rules
```python
def format_intervals(components):
    """
    Build Intervals.icu formatted string

    Rules:
    - Base run always first (if exists)
    - Blank line before interval block
    - Standalone "Nx" line
    - Work + recovery steps with "-" prefix
    - Blank line after interval block (if cooldown follows)
    - NO nesting - flatten all intervals
    """
    lines = []

    # Base run
    if components.base_duration > 0:
        lines.append(f"- {format_duration(components.base_duration)} {components.base_intensity}")
        lines.append("")  # Blank line

    # Interval block
    if components.intervals:
        lines.append(f"{components.reps}x")
        lines.append(f"- {format_duration(components.work_duration)} {components.work_intensity}")
        lines.append(f"- {format_duration(components.recovery_duration)} {components.recovery_intensity}")
        lines.append("")  # Blank line after intervals

    # Cooldown
    if components.cooldown_duration > 0:
        lines.append(f"- {format_duration(components.cooldown_duration)} {components.cooldown_intensity}")

    return "\n".join(lines).strip()
```

### Format Specification Document Structure

See `INTERVALS_FORMAT_SPEC.md` at repo root.

### Testing Strategy

#### Test cases
```python
TEST_CASES = [
    {
        "input": {
            "description": "Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )",
            "duration_seconds": 2700  # 45 minutes
        },
        "expected_output": """- 18m z2 pace

7x
- 17s z5 pace
- 1m45s z2 pace""",
    },
    {
        "input": {
            "description": "15:00 Easy (Z1-Z2) 2x( 10:00 @ HMP (Z4) 5:00 Walk / Easy Jog recovery ) 5:00 Easy (Z1-Z2)",
            "duration_seconds": 2700  # 45 minutes
        },
        "expected_output": """- 15m z2 pace

2x
- 10m z4 pace
- 5m z2 pace

- 5m z2 pace""",
    },
    {
        "input": {
            "description": "30min easy",
            "duration_seconds": 1800
        },
        "expected_output": "- 30m z2 pace",
    },
]
```

### Implementation Roadmap

#### Phase 1 ✅ — Format specification document
Create `INTERVALS_FORMAT_SPEC.md` at repo root.

#### Phase 2 ✅ — Parser for common patterns
- Parenthetical `Nx(work / recovery)` form
- Inline `N x work [sep] recovery` prose form
- Strides/pickups keyword template (5 × 15 s z5 / 1m45s z1)
- Simple single-step fallback

#### Phase 3 ✅ — Range resolution logic
- Duration midpoint, rep midpoint-rounded-down
- Intensity mapping table
- `->` arrow notation (MP->HMP → z4)

#### Phase 4 ✅ — Integration into MCP server
- `create_event` and `bulk_create_events` call `translate_workout()` automatically
- `translation_quality` field logged for observability

#### Phase 5 — Deterministic bug fixes + Local LLM fallback (PLAN OF RECORD)

**Status**: In design. These are the remaining known failure categories from
the pre-marathon translation test (6 ✅ · 4 ⚠️ · 4 ❌).

##### Phase 5a — Deterministic fixes (implement first, low risk)

Four bugs with well-defined structural signatures that don't require an LLM:

**P4 — `on`/`off` intensity mapping** (trivial)
- Root cause: "30s on / 2 mins off" — `on` and `off` not in `INTENSITY_MAP`
- Fix: Add `"on": "z5 pace"` and `"off": "z1 pace"` to the map
- Risk: None

**P3 — Non-bullet multi-segment descriptions**
- Root cause: `45 mins easy\n30mins at MP\n15 mins cool down` (no `- ` prefix)
  falls through `_parse_bullet_list` because it only matches `^-\s` lines
- Fix: Add `_parse_plain_segments()` — iterate lines, call `_parse_step_fragment`
  on each, accept result if ≥ 2 lines parse successfully; insert between bullet
  check and inline check in `_translate()`
- Risk: Very low

**P2 — Commentary-bullet bleed**
- Root cause: Coaching-cue bullets like `- By effort*`, `- Total Workout Time: 48 mins`,
  `- Aim for 80-90 mins total` treated as workout steps
- Fix: `_is_commentary_bullet(content)` filter applied in `_parse_bullet_list` before
  step parsing:
  ```python
  _COMMENTARY_RE = re.compile(
      r"^(by\s|total\s|aim\s|note[:\s]|start\s|priority\s|if\s|goal[:\s]|"
      r"cool\s+down\s+to|hitting\s|practice\s)",
      re.IGNORECASE,
  )
  _ARITHMETIC_RE = re.compile(r"\d+\s*\w+\s*\+\s*\d+")  # "20 easy + 48 w/o"

  def _is_commentary_bullet(content: str) -> bool:
      if _COMMENTARY_RE.match(content):
          return True
      if _ARITHMETIC_RE.search(content):
          return True
      return False
  ```
- Risk: Low; keyword list scoped to observed coach format patterns

**P1 — `m` = meters vs minutes disambiguation**
- Root cause: `200m`, `400m`, `800m`, `1600m` parsed as 200–1600 minutes
- Fix: magnitude-based pre-filter `_is_meters_not_minutes(value)`:
  ```python
  _METER_DISTANCES = {100, 150, 200, 300, 400, 600, 800, 1000, 1200, 1500, 1600, 3000, 5000}
  _MINUTE_THRESHOLD = 90  # Xm where X > 90 is never a valid minute count

  def _is_meters_not_minutes(value: float) -> bool:
      v = int(value)
      return v in _METER_DISTANCES or v > _MINUTE_THRESHOLD
  ```
  When a token is identified as meters, return `None` for duration; bubble up as
  `WorkoutTranslationError("distance-based intervals")` so it falls through to
  Phase 5b LLM.
- Risk: Very low; threshold of 90 min is safe for all realistic step durations

##### Phase 5b — Local LLM fallback (implement after 5a, benchmark against 5a)

**Motivation**: After Phase 5a, the remaining hard failures are structurally
ambiguous — multi-segment prose with no bullets, nested conditions, or novel
formats the regex can't anticipate. A local LLM handles these without
additional rule engineering.

**Model candidates** (benchmarked for structured output reliability):

| Model | Size (Q4) | Est. latency (CPU) | Notes |
|-------|-----------|-------------------|-------|
| Phi-3-mini-4k | ~2.2 GB | ~2–4 s | Best size/quality for structured output |
| Mistral-7B-Instruct | ~4.1 GB | ~5–10 s | More robust on ambiguous prose |
| Llama-3.2-3B-Instruct | ~2.0 GB | ~2–3 s | Strong instruction following for size |

**Recommended starting point**: Phi-3-mini via `ollama`. Upgrade to Mistral-7B
if output quality is insufficient on the benchmark set.

**Runtime options**:
- `ollama` (recommended): single `ollama serve` background process; Python
  client via `requests` or `ollama` pip package; no GPU required
- `llama-cpp-python`: direct embedding in the MCP process, no side process;
  slightly more setup
- `ctransformers`: fallback if llama-cpp-python has build issues on Windows

**Prompt design**:
```
System:
You are a workout translator. Convert FinalSurge workout descriptions to
Intervals.icu plain-text format. Rules:
- Steps start with "- " (dash space)
- Duration: 30m, 15s, 1h, 1m30s (m = minutes, s = seconds, NOT meters)
- Intensity: z1–z5 pace (z1=recovery, z2=easy, z3=tempo, z4=threshold/HMP, z5=hard/strides)
- Repeat blocks: standalone "Nx" line, then steps, blank lines before/after
- No nested repeats
- Distance-based intervals (200m, 800m etc.): estimate step duration from total
  workout time and rep count

Return ONLY the formatted workout. No explanation.

Example 1:
Duration: 45m
Description: Easy running throughout 6-8x( 15-20s @ Stride / Fast (Z5) Full recovery easy jog )
Output:
- 18m z2 pace

7x
- 17s z5 pace
- 1m45s z2 pace

Example 2:
Duration: 1h20m
Description: 8 x 4:00mins @MP->HMP and 2:00mins easy
Output:
- 32m z2 pace

8x
- 4m z4 pace
- 2m z2 pace

User:
Duration: {total_duration}
Description: {description}

Output:
```

**Integration in `_translate()`**:
```python
def _translate(description, duration_seconds, sport_type):
    try:
        # ... Phase 1–4 regex pipeline ...
    except WorkoutTranslationError as exc:
        logger.info("Regex pipeline failed (%s), trying LLM fallback.", exc)
        if _llm_available():
            return _translate_with_llm(description, duration_seconds, sport_type)
        logger.warning("LLM unavailable, returning simple fallback.")
        return _build_simple(description, duration_seconds, sport_type)
```

**`translation_quality` values** (for observability):
- `"structured"` — paren or inline Nx form parsed deterministically
- `"template"` — strides/pickups template applied
- `"bullet_list"` — multi-bullet list parsed
- `"plain_segments"` — non-bullet multi-line parsed (Phase 5a)
- `"llm"` — LLM fallback used (Phase 5b)
- `"simple_fallback"` — neither pipeline succeeded

##### Phase 5c — Benchmark: regex+LLM vs straight-to-LLM

**Purpose**: Determine whether the regex pre-pipeline is worth maintaining
long-term vs. routing everything through the LLM.

**Validation test set**: The 10 structured runs immediately preceding the Feb 1
half marathon, taken from `workout_translations.md`. These are the best test
cases because they are the most complex workouts in the plan (peak training
weeks) and all have known expected outputs from the earlier translation run.

| Date | Workout | Key challenge |
|------|---------|---------------|
| 2026-01-24 | Last Workout! | Non-bullet multi-segment (P3) |
| 2026-01-23 | Easy Run with Strides | Strides template |
| 2026-01-20 | Cutdown | Distance-based (`1600m`, `1200m`, etc.) (P1) |
| 2026-01-17 | Last Big Workout! | Non-bullet multi-segment (P3) |
| 2026-01-16 | Easy Run w/Strides | Strides template |
| 2026-01-14 | Easy Run w/4-6 strides | Strides keyword |
| 2026-01-13 | 600s | Commentary-bullet bleed (P2) |
| 2026-01-10 | Long Run with Pickups | `on`/`off` intensity (P4) |
| 2026-01-08 | Tempo + Pickups | `on`/`off` intensity (P4) |
| 2026-01-06 | Easy Run w/Strides | Strides template |

This set covers all four P1–P4 bug categories plus the strides template,
making it the minimum viable benchmark corpus.

**Benchmark protocol**:
1. Run both approaches (regex+LLM hybrid, straight-to-LLM) against all 10 workouts
2. Metrics:
   - **Correctness**: manual review; score each output 0/0.5/1 against expected
   - **Speed**: wall-clock time per workout (seconds)
   - **Total pipeline time**: for a realistic weekly sync (assume 8–12 workouts)
3. Expected hypothesis: regex handles ~60% of workouts in <1ms each; LLM covers
   the rest in ~3–8s; straight-to-LLM is simpler but ~3–8s for every workout
   including the easy ones

**Decision criteria**:
- If straight-to-LLM correctness ≥ regex+LLM and total time is acceptable
  (< 2 min for a full week sync), retire the regex pipeline and simplify
- If regex+LLM is meaningfully faster AND comparably correct, keep hybrid
- The regex pipeline is also the documentation of intent (what each format
  pattern means), so has archival value even if LLM wins on correctness alone

##### Phase 5d — Future: structured output enforcement

If the LLM produces occasional format violations (missing dash, wrong duration
unit), add a lightweight post-processor that validates the output against
`INTERVALS_FORMAT_SPEC.md` rules and either auto-corrects or re-prompts once.

### Function Location in MCP Server

```
src/intervals_icu_mcp/
├── workout_translator.py      # Regex pipeline + LLM dispatch
├── workout_translator_llm.py  # LLM fallback (Phase 5b)
└── tools/
tests/
├── test_translator.py
└── test_translator_llm.py     # Phase 5b/5c benchmarks
```

### API Changes

**New optional parameter on create_event**:
```python
def create_event(
    ...,
    auto_translate: bool = True,
    ...
):
    if auto_translate and description:
        description = translate_workout(description, duration_seconds, event_type)
    # ... rest of implementation
```

### Edge Cases to Handle

1. **Ambiguous ranges**: "6-8x" → default to midpoint rounded down (7x)
2. **Missing intensity**: default to z2 for base, z2 for recovery
3. **"Full recovery"**: calculate from remaining time
4. **Nested parentheses**: flatten to single level
5. **Multiple interval blocks**: NOT supported - fail with clear error
6. **Unknown terms**: log warning, use conservative defaults
7. **Distance-based intervals** (`200m`, `800m`): detected by magnitude heuristic,
   routed to LLM fallback (Phase 5b) which can estimate duration from total time

### Error Handling

```python
class WorkoutTranslationError(Exception):
    """Raised when translation cannot proceed."""
    pass

def translate_workout(...):
    try:
        return _translate(...)
    except WorkoutTranslationError as e:
        logger.warning(f"Translation failed: {e}. Using original description.")
        return description
```

### Documentation Updates Needed

1. MCP tool description: Add `auto_translate` parameter docs
2. README: Add translation examples
3. Phase 5b: Add `ollama` setup instructions to README (model pull command,
   background service setup on Windows)
