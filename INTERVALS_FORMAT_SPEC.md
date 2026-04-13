# Intervals.icu Workout Format Specification
Reference for automated FinalSurge → Intervals.icu translation

## Core Syntax Rules

### Step Format
```
- [duration OR distance] [intensity] [optional_cadence]
```

**MUST start with `-` (dash + space)**

Examples:
```
- 30m z2 pace
- 15s z5 pace
- 1m45s z2 pace
- 10m 75% 90rpm
```

## Duration Formats

| Format | Example | Notes |
|--------|---------|-------|
| Minutes | `30m`, `5m` | **`m` = minutes, NOT meters** |
| Seconds | `15s`, `90s` | |
| Combined | `1m30s`, `1h2m30s` | |
| Hours | `1h`, `2h30m` | |
| Shorthand | `5'`, `30"`, `1'30"` | Optional, prefer full format |

**Critical**: Never use `m` for meters. Use `km` or `mi` for distance.

## Intensity Formats

### Running (Pace-based)
```
z1 pace    # Recovery (70-75% of pace)
z2 pace    # Easy (76-80%)
z3 pace    # Tempo (81-88%)
z4 pace    # Threshold/HMP (89-95%)
z5 pace    # VO2 Max/Strides (96-105%)
z6 pace    # Sprint (>105%)
```

Alternative formats:
```
78-82% pace      # Percentage range
90% pace         # Single percentage
```

### Heart Rate
```
70% HR           # Percentage of max
75-80% HR        # Range
95% LTHR         # Percentage of threshold
Z2 HR            # Zone-based
```

### Cycling (Power)
```
75%              # Percentage of FTP
200-240w         # Watts range
Z2               # Zone
ramp 50%-75%     # Gradual increase
```

## Interval/Repeat Syntax

### Two Valid Forms

**Form 1: Section Header**
```
Main Set 6x
- 15s z5 pace
- 1m45s z2 pace
```

**Form 2: Standalone Line** (RECOMMENDED for clarity)
```
6x
- 15s z5 pace
- 1m45s z2 pace
```

### Required Formatting Around Repeats

**CRITICAL**: Blank lines MUST surround repeat blocks

```
- 18m z2 pace
                   ← BLANK LINE REQUIRED
6x
- 15s z5 pace
- 1m45s z2 pace
                   ← BLANK LINE REQUIRED (if more steps follow)
- 5m z2 pace
```

### Nested Repeats: NOT SUPPORTED

❌ **INVALID**:
```
3x
- 10m z3 pace
- 2x                 ← Nested repeat
  - 30s z5 pace
  - 30s z2 pace
```

✅ **VALID** (flatten the structure):
```
3x
- 10m z3 pace
- 30s z5 pace
- 30s z2 pace
- 30s z5 pace
- 30s z2 pace
```

## Section Headers

Lines without `-` are treated as headers/labels:
```
Warmup
- 10m z2 pace

Main Set 6x
- 15s z5 pace
- 1m45s z2 pace

Cooldown
- 5m z2 pace
```

## Text Prompts/Cues

**Basic cue**: Text before duration/intensity
```
- Recovery 30s z1 pace     # Cue displays as "Recovery"
```

**Timed prompts**: Use `time^message <!> step`
```
- First cue 30^Second cue <!> 10m ramp 50-75%
```

## Complete Workout Structure Examples

### Simple Run
```
- 30m z2 pace
```

### Run with Strides
```
- 18m z2 pace

7x
- 17s z5 pace
- 1m45s z2 pace
```

### Structured Interval Workout
```
Warmup
- 15m z2 pace

Main Set 2x
- 10m z4 pace
- 5m z2 pace

Cooldown
- 5m z2 pace
```

## Common FinalSurge → Intervals.icu Mappings

### Intensity Terms
| FinalSurge | Intervals.icu |
|------------|---------------|
| "easy", "easy jog" | `z2 pace` |
| "recovery" | `z1 pace` |
| "tempo" | `z3 pace` |
| "threshold", "@threshold" | `z4 pace` |
| "HMP", "@HMP" | `z4 pace` |
| "stride", "strides", "fast" | `z5 pace` |
| "sprint" | `z6 pace` |

### Duration Patterns
| Pattern | Resolution | Example |
|---------|------------|---------|
| "15-20s" | Midpoint | `17s` |
| "6-8x" | Midpoint rounded down | `7x` |
| "Full recovery" | Calculate from total time | `1m45s` |

## Formatting Checklist

- [ ] All steps start with `-` (dash space)
- [ ] Blank line before repeat block
- [ ] Standalone `Nx` line (not inline)
- [ ] Blank line after repeat block (if more steps follow)
- [ ] No nested repeats
- [ ] Duration uses `m` for minutes (not meters)
- [ ] Intensity includes unit (`pace`, `HR`, `%`, etc.)
- [ ] Total duration matches expected workout length

## Error Prevention

### Common Mistakes
❌ Missing dash: `30m z2 pace`
✅ Correct: `- 30m z2 pace`

❌ No blank line: 
```
- 18m z2 pace
6x
```
✅ Correct:
```
- 18m z2 pace

6x
```

❌ Inline repeat: `- 6x 15s z5 pace`
✅ Correct:
```
6x
- 15s z5 pace
```

❌ Nested repeat:
```
2x
- 10m z3
- 3x
  - 30s z5
```
✅ Correct: Flatten or multiply out

## Parsing Priority

When translating natural language:

1. **Identify repeat pattern**: Look for `Nx(...)` or `N-Mx(...)`
2. **Extract intensities**: Zone markers, pace descriptors
3. **Extract durations**: Specific times or ranges
4. **Calculate base run**: `total_duration - (reps × (work + recovery))`
5. **Resolve ranges**: Use midpoint for durations, round down for reps
6. **Format with blank lines**: Always surround repeat blocks
7. **Validate total duration**: Ensure steps sum to expected time

## Translation Decision Tree

```
Is there an interval pattern (Nx)?
├─ YES
│  ├─ Extract: reps, work duration, recovery description
│  ├─ Calculate work time from duration or default
│  ├─ Calculate recovery time from total - work
│  ├─ Build: base run + blank + Nx + work + recovery + blank + cooldown
│  └─ Validate: total time matches
└─ NO
   └─ Simple step: "- {duration} {intensity}"
```

## Validation Rules

After translation, verify:
1. Total duration = sum of all step durations × repetitions
2. No text before first `-` except section headers
3. All `Nx` lines are standalone (no `-` prefix)
4. Blank lines present before/after `Nx` blocks
5. All steps have duration AND intensity
6. Intensity format matches sport type (pace for runs, power/watts for rides)
