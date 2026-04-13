# FinalSurge → Intervals.icu Translations: Pre-Marathon Block
*Generated 2026-04-09 — last 20 runs before 2026-02-01 Surf City Marathon*
*Translated with `workout_translator.py` post Phase-4 + bullet-list parser + strides template + recovery z1 fixes*

**Parser quality legend:** ✅ correct · ⚠️ minor issue · ❌ broken (distance-based "m=meters" bug or commentary bleed)

---

## 2025-12-23 | 200s and Miles (80 min) ❌

**FinalSurge description:**
```
2 sets of :
- 4 x 200m@3k-5k (45-55s), with 200m jog rest*
- 2 Mile Tempo at 7:55-8:15
- 3 mins rest between sets

If you don't have access to a track, then swap the 200s for 1 min on, 1 min off
```

**Intervals.icu translation:**
```
4x
- 3h20m z2 pace
- 3h20m z1 pace

- 31m30s z3 pace
- 3m z1 pace
```

> ❌ **Broken — distance-based "m = meters" bug.** `200m` is parsed as 200 minutes (3h20m).
> `2 Mile Tempo` → "2 Mile" has no time unit, so falls through; "7:55-8:15" midpoint becomes
> 31m30s which is a pace annotation, not a duration. "3 mins rest" → 3m z1 (correct in isolation).
>
> **Phase-5 fix needed:** disambiguate metric/imperial distances from minute durations.
> Heuristic: if value > ~30 and immediately followed by `m` (no following digit/colon), treat as meters.

---

## 2025-12-27 | Pace Change tempo (70 min) ❌

**FinalSurge description:**
```
3-4 miles of continuous tempo:
- 400m@HMP (~8:15-30 pace)
- 1200m@MP (8:40-9)

The goal of this workout is to manage the change in pace...
```

**Intervals.icu translation:**
```
- 6h40m z4 pace
- 20h z3 pace
```

> ❌ **Broken — distance-based "m = meters" bug.** `400m` → 400 min (6h40m), `1200m` → 1200 min (20h).
> Same root cause as 200s and Miles above.

---

## 2025-12-28 | Long Run (120 min) ✅

**FinalSurge description:**
```
Easy pace
```

**Intervals.icu translation:**
```
- 2h z2 pace
```

> ✅ Simple description, correct fallback.

---

## 2025-12-30 | Cutdown (75 min) ❌

**FinalSurge description:**
```
Priority this weekend is the weekend workout...
- 1.5 miles@HMP or 8:05-15 per mile, 2 mins rest
- 1.25 miles@HMP or quicker, 8:00-8:10 per mile, 2 mins rest
- 1 mile @HMP or quicker 7:50-8:00 per mile, 2 mins rest
- 0.5 mile@10k pace or 7:30-7:45mins per mile (3:45-3:52mins)
```

**Intervals.icu translation:**
```
- 8m5s z1 pace
- 4m z1 pace
- 29m z1 pace
- 18m30s z2 pace
```

> ❌ **Broken — pace annotations parsed as durations.** "8:05-15" → 8m5s, "8:00-8:10" → 4m (midpoint),
> "7:50-8:00" → 29m (range badly computed), "7:30-7:45" → 18m30s.
> The values are min/mile pace, not workout step durations. All steps come out as z1 because "HMP" or
> "rest" is the dominant intensity token after pace annotation is consumed.
>
> **Phase-5 fix needed:** detect "X miles@pace or Y:ZZ per mile" pattern → mark as distance-based,
> skip or fall back to simple.

---

## 2026-01-02 | Easy Run w/4-6 strides (45 min) — *no description*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 45m z2 pace
```

> No description — fallback to total duration at z2.
> **Note:** Name contains "strides" but strides template only fires on *description* content.
> Phase-5 could fall back to the strides template when the workout *name* matches.

---

## 2026-01-04 | Marathon Checkpoint (130 min) ⚠️

**FinalSurge description:**
```
- 30 mins easy warm up
- 4 x 15mins at MP with 5 mins rest (walk or easy jog) (1hr 15)
- Start slower at like 8:45-50 pace, then ok to cutdown the pace
- 15-25 mins cool down
```

**Intervals.icu translation:**
```
- 30m z2 pace

4x
- 15m z3 pace
- 5m z1 pace

- 8m45s z2 pace
- 20m z2 pace
```

> ⚠️ **Mostly correct, one spurious commentary step.** The warm-up (30m z2) ✓, the interval
> block (4x 15m@MP + 5m z1 recovery) ✓ — recovery correctly z1 because "(walk or easy jog)"
> is stripped by paren removal, leaving "rest" → z1. The cooldown (15–25 min midpoint = 20m z2) ✓.
>
> **Issue:** "Start slower at like 8:45-50 pace" is a coaching cue, not a step. The colon-time
> pattern `8:45` (8 min 45 s) is parsed as a 8m45s duration. This is a commentary-bullet bleed.
>
> **Phase-5 fix:** filter bullets that contain no standalone time unit after removing pace annotations
> (i.e., "8:45-50 *per mile*" should be disqualified as a step duration).

---

## 2026-01-06 | Easy Run w/Strides (40 min) ✅

**FinalSurge description:**
```
4 x 100m strides with full rest (or 15-20s pickups)
```

**Intervals.icu translation:**
```
- 30m z2 pace

5x
- 15s z5 pace
- 1m45s z1 pace
```

> ✅ **Strides template applied.** "strides" + "pickups" detected → standard 5×(15s z5 / 1m45s z1).
> Base run = 40 min − 10 min intervals = 30 min z2.

---

## 2026-01-08 | Tempo + Pickups (80 min) ❌

**FinalSurge description:**
```
- 3-5 miles@HMP
- take full rest
- 4-6 x 30s on / 2 mins off
```

**Intervals.icu translation:**
```
5x
- 30s z2 pace
- 2m z2 pace
```

> ❌ **Broken — two issues.**
> 1. `3-5 miles@HMP` is distance-based; no duration parsed → entire HMP tempo segment dropped.
> 2. `4-6 x 30s on / 2 mins off` → 5x correctly, but `"on"` has no intensity mapping → z2 (should
>    be z5). `"off"` → z2 (should be z1). The word "Pickups" is in the *name* not description.
>
> **Phase-5 fixes needed:**
> - Map `"on"` → `z5 pace` (or detect as the work keyword in "Xon / Yoff" patterns).
> - Map `"off"` → `z1 pace`.
> - Handle distance-only tempo bullets with a fallback (e.g., estimate from total time).

---

## 2026-01-09 | Easy Run w/4-6 strides (45 min) — *no description*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 45m z2 pace
```

> No description — fallback to total duration at z2.

---

## 2026-01-10 | Long Run with Pickups (140 min) ⚠️

**FinalSurge description:**
```
10-12 x 30s on and 2 mins off easy jog

- 30 mins easy
- 60 mins easy-> moderate
- 30 mins of workout (30s on / 2 off)
- 10-20mins easy cool down
```

**Intervals.icu translation:**
```
- 30m z2 pace
- 1h z2 pace
- 30m z2 pace
- 15m z2 pace
```

> ⚠️ **Segment structure captured, interval detail lost.** The 4 bullet lines correctly describe
> the time blocks: 30m easy, 60m easy-moderate, 30m workout, 10–20m cooldown → 135m total (≈ 140m ✓).
> All resolve to z2 which is reasonable for a mostly-easy long run.
>
> The interval detail (`10-12 x 30s on / 2 off`) is in the non-bullet header line and is ignored
> by the bullet-list parser. "easy->" moderate → arrow notation → z2 (correct for the build portion).
>
> **Phase-5:** parse non-bullet header lines alongside bullets; detect embedded Nx in header.

---

## 2026-01-13 | 600s (70 min) ⚠️

**FinalSurge description:**
```
- 8 x 600m@Tempo 8:20-30ish pace or 3:07-10 (200m jog rest)
- If you don't have access to a track, swap to 3 mins on / 1 off

Priority is the weekend workout...
```

**Intervals.icu translation:**
```
8x
- 8m20s z3 pace

- 3m z2 pace
```

> ⚠️ **Rep count and intensity correct; duration and fallback step wrong.**
> `8x` ✓. `z3 pace` (Tempo) ✓.
> Duration: `8:20` (pace annotation in "8:20-30ish pace") parsed as 8 min 20 s — that's actually
> the right *order of magnitude* for 8 × 600m tempo reps (true rep ≈ 3:07–3:10 each; 8 × 3:09 = 25m,
> but the pace per mile "8:20" accidentally works as a plausible proxy duration at 8m20s).
> However it is semantically wrong (pace ≠ duration).
>
> The correct rep duration `3:07-10` was in parentheses and stripped. `(200m jog rest)` also stripped.
>
> Second bullet "If you don't have access to a track, swap to 3 mins on / 1 off" → `3m z2` (commentary parsed as step).
>
> **Phase-5 fix:** prefer the parenthesised `MM:SS` if present (currently stripped); filter commentary bullets.

---

## 2026-01-14 | Easy Run w/4-6 strides (30 min) — *no description*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 30m z2 pace
```

> No description — fallback to total duration at z2.

---

## 2026-01-16 | Easy Run w/Strides (40 min) ✅

**FinalSurge description:**
```
4 x 100m strides with full rest (or 15-20s pickups)
```

**Intervals.icu translation:**
```
- 30m z2 pace

5x
- 15s z5 pace
- 1m45s z1 pace
```

> ✅ Identical description to 2026-01-06. Strides template applied correctly.

---

## 2026-01-17 | Last Big Workout! (150 min) ⚠️

**FinalSurge description:**
```
Total Time: 2:30-2:45
- Hitting total time is first priority, but only do 2:45 if you are feeling good
- Practice this like race day, and start slower than you think you need to :)

Workout:
- 45 mins easy
- 2 x 40mins@MP(8:40-55) with 10 mins easy rest in between
- 15-30 mins easy
```

**Intervals.icu translation:**
```
- 2m45s z2 pace
- 45m z2 pace

2x
- 40m z3 pace
- 10m z1 pace

- 22m30s z2 pace
```

> ⚠️ **Core workout correct; two commentary bullets bleed through.**
>
> ✅ The key block: `2x 40m@MP + 10m recovery` — MP → z3 ✓, recovery (`"easy rest"`) → z1 ✓.
> ✅ Cooldown 15–30 min midpoint → 22m30s z2 ✓.
>
> ❌ Bullet "only do 2:45 if you are feeling good" → `2:45` colon pattern → 2m45s spurious step.
> ❌ Bullet "Practice this like race day..." → no duration parsed → correctly dropped ✓.
> ❌ Bullet "Hitting total time..." → no duration → dropped ✓.
>
> **Phase-5 fix:** filter commentary bullets (e.g., bullets with no standalone min/sec unit outside
> a pace context).

---

## 2026-01-20 | Cutdown (60 min) ❌

**FinalSurge description:**
```
4400k Cutdown - 2mins rest all
- 1600m@Tempo->10k (8:30? who knows after the last big workout lol)
- 1200m@10k ~5:40-50 or 1:53ish per 400m
- 800m@5k ~3:40-50 or 1:50ish per 400m
- 400m@3k ~1:40
- 2 x 200m@Mile, 48-52s
```

**Intervals.icu translation:**
```
- 26h40m z3 pace
- 5m40s z2 pace
- 3m40s z2 pace
- 1m40s z2 pace

2x
- 50s z2 pace
```

> ❌ **Broken — distance-based "m = meters" bug throughout.**
> `1600m` → 1600 min (26h40m), `1200m` → 1200 min, `800m` → 800 min, `400m` → 400 min.
> The `2 x 200m` → 2x with 200 min work (shown as `50s` because midpoint of `48-52s` was found first).
> Effectively unusable. Same root cause as the other distance-based workouts.

---

## 2026-01-23 | Easy Run with Strides (25 min) ✅

**FinalSurge description:**
```
Run 4-6 x 100m or 15-20s pickups, with full recovery
```

**Intervals.icu translation:**
```
- 15m z2 pace

5x
- 15s z5 pace
- 1m45s z1 pace
```

> ✅ Strides template: 25 min − 10 min = 15 min base run. Correct.

---

## 2026-01-24 | Last Workout! (90 min) ⚠️

**FinalSurge description:**
```
45 mins easy to moderate
30mins at goal marathon pace: 8:40-9:00
15 mins cool down

If feeling tired, shorten even more! Cutdown the 45mins to 30
```

**Intervals.icu translation:**
```
- 1h30m z3 pace
```

> ⚠️ **No bullet lines → simple fallback.** "marathon pace" found in full description → z3 pace.
> Duration = total 90m. The three-segment structure (45m easy + 30m MP + 15m cooldown) is not
> captured because there are no bullet lines to trigger the bullet-list parser, and no Nx repeat.
>
> **Phase-5 fix:** detect non-bullet multi-segment descriptions (lines with explicit durations
> separated by newlines) and parse them the same way as bullet lists.

---

## 2026-01-27 | Pre-Race! (45 min) ❌

**FinalSurge description:**
```
2-3 x Mile Progressive with 90s rest
- Marathon Pace -> Half Pace -> 10k pace
- 8:45-9:00 to 8:30-45 to 8:15-30 (roughly)
- Take 3-5mins rest
- then run 2-4 x 200m@5k (or faster than last mile repeat) with 200m jog rest
```

**Intervals.icu translation:**
```
- 27m z2 pace
- 4m z1 pace

3x
- 3h20m z2 pace
- 3h20m z1 pace
```

> ❌ **Broken — distance + pace annotation confusion throughout.**
> Bullet-list parser fires (4 bullets). `200m` → 200 min (3h20m) — distance bug again.
> `8:45-9:00` in bullet 2 → pace annotation parsed as time range.
> The `3x` block represents "2-4 x 200m@5k" which is valid structurally but the duration is nonsense.
> `- 27m z2 pace` comes from the 4-minute rest bullet ("Take 3-5mins rest" midpoint = 4m z1 — shown
> above the 3x block because... actually this is from the `90s` rest in the non-bullet header line
> being parsed by `_parse_surrounding`).

---

## 2026-01-30 | Easy Run (30 min) ✅

**FinalSurge description:**
```
Run 6-8 x 100m or 15-20s pickups, with full recovery
```

**Intervals.icu translation:**
```
- 20m z2 pace

5x
- 15s z5 pace
- 1m45s z1 pace
```

> ✅ Strides template: 30 min − 10 min = 20 min base run.

---

## 2026-01-31 | Easy Run w/Strides (20 min) ✅

**FinalSurge description:**
```
Run 4-6 x 100m or 15-20s pickups, with full recovery
```

**Intervals.icu translation:**
```
- 10m z2 pace

5x
- 15s z5 pace
- 1m45s z1 pace
```

> ✅ Strides template: 20 min − 10 min = 10 min base run.

---

## Summary

| Date | Workout | Duration | Quality | Parser path |
|------|---------|----------|---------|-------------|
| 2025-12-23 | 200s and Miles | 80 min | ❌ | bullet-list, m=meters bug |
| 2025-12-27 | Pace Change tempo | 70 min | ❌ | bullet-list, m=meters bug |
| 2025-12-28 | Long Run | 120 min | ✅ | simple (easy pace) |
| 2025-12-30 | Cutdown | 75 min | ❌ | bullet-list, pace=duration confusion |
| 2026-01-02 | Easy Run w/4-6 strides | 45 min | — | no-desc fallback |
| 2026-01-04 | Marathon Checkpoint | 130 min | ⚠️ | bullet-list + inline Nx, 1 commentary step |
| 2026-01-06 | Easy Run w/Strides | 40 min | ✅ | strides template |
| 2026-01-08 | Tempo + Pickups | 80 min | ❌ | bullet-list, distance drop + "on/off" unmapped |
| 2026-01-09 | Easy Run w/4-6 strides | 45 min | — | no-desc fallback |
| 2026-01-10 | Long Run with Pickups | 140 min | ⚠️ | bullet-list, segments correct, intervals lost |
| 2026-01-13 | 600s | 70 min | ⚠️ | bullet-list + inline Nx, rep count+intensity ✓, duration wrong, commentary step |
| 2026-01-14 | Easy Run w/4-6 strides | 30 min | — | no-desc fallback |
| 2026-01-16 | Easy Run w/Strides | 40 min | ✅ | strides template |
| 2026-01-17 | Last Big Workout! | 150 min | ⚠️ | bullet-list + inline Nx, core correct, 1 commentary step |
| 2026-01-20 | Cutdown | 60 min | ❌ | bullet-list, m=meters bug throughout |
| 2026-01-23 | Easy Run with Strides | 25 min | ✅ | strides template |
| 2026-01-24 | Last Workout! | 90 min | ⚠️ | simple fallback (no bullets), loses segment structure |
| 2026-01-27 | Pre-Race! | 45 min | ❌ | bullet-list, m=meters + pace annotation confusion |
| 2026-01-30 | Easy Run | 30 min | ✅ | strides template |
| 2026-01-31 | Easy Run w/Strides | 20 min | ✅ | strides template |

**Score: 6 ✅ · 4 ⚠️ · 4 ❌ · 3 no-desc (fallback)**

---

## Phase-5 Bug Priority List

Ordered by frequency and impact across this dataset:

### P1 — `m` disambiguation (meters vs. minutes)
Affects: 200s and Miles, Pace Change tempo, Cutdown ×2, Pre-Race! (5 workouts broken)

Distance values like `200m`, `400m`, `600m`, `800m`, `1200m`, `1600m` are parsed as minutes.
**Heuristic:** if a bare integer > 30 is immediately followed by `m` (and not followed by another
digit or `/km`), treat it as meters and skip the duration parse for that token.

### P2 — Commentary-bullet bleed
Affects: Marathon Checkpoint, Last Big Workout!, 600s (3 workouts with spurious steps)

Bullet lines that are coaching cues (not workout steps) are parsed as steps because they happen
to contain time-like strings (`2:45`, pace ranges like `8:20-30`).
**Heuristic:** a bullet line whose *only* numeric token is a pace annotation (i.e., `HH:MM` preceded
or followed by "pace", "per mile", "per km", or a slash-fraction) should be excluded from step parsing.

### P3 — Non-bullet multi-segment descriptions
Affects: Last Workout! (1 workout)

Three-part structure `45 mins easy\n30mins at MP\n15 mins cool down` (no dashes) falls through to
the simple parser. Extend bullet-list logic to also handle plain newline-separated duration lines.

### P4 — `"on"` / `"off"` intensity keywords
Affects: Tempo + Pickups, Long Run with Pickups

`"30s on / 2 mins off"` pattern: `"on"` should map to z5, `"off"` to z1.
Add to `INTENSITY_MAP`: `"on": "z5 pace"`, `"off": "z1 pace"`.

### P5 — Strides template triggered by workout *name* (no description)
Affects: 3 no-description strides workouts

When description is empty but workout name contains "strides" or "pickups", apply the strides
template instead of the plain `- Nm z2 pace` fallback.
