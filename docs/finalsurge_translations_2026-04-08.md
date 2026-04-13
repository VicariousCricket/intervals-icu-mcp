# FinalSurge → Intervals.icu Translations
*Generated 2026-04-08 — last 10 named runs from FinalSurge (60-day window)*

Translations produced by `workout_translator.py` (post Phase-4 + bullet-list parser).
Each entry shows the FinalSurge description and the resulting Intervals.icu `description` field.

---

## 2026-03-18 | Easy Run (30 min) — *Planned*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 30m z2 pace
```

> **Note:** No description — fallback to total duration at z2.

---

## 2026-03-20 | Easy Run with Strides (30 min) — *Planned*

**FinalSurge description:**
```
Run 6-8 x 100m or 15-20s pickups, with full recovery
```

**Intervals.icu translation:**
```
- 28m1s z2 pace

7x
- 17s z1 pace
```

> **Parser path:** inline `Nx` (6–8 → 7x). Work = 17s (midpoint of 15–20s). No explicit recovery
> duration (distance-based: 100m), so recovery time is absorbed into the base run.
>
> **Known issue:** Stride intensity resolves to `z1 pace` because the intensity scanner reaches
> "recovery" in the phrase "with full recovery" before it finds "pickups". The `17s` step should
> ideally be `z5 pace`. Flagged for Phase-5 prompt-assisted fix.

---

## 2026-03-24 | Easy Run (30 min) — *Planned*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 30m z2 pace
```

> **Note:** No description — fallback to total duration at z2.

---

## 2026-03-27 | Easy Run with Strides (45 min) — *Planned*

**FinalSurge description:**
```
Run 6-8 x 100m or 15-20s pickups, with full recovery
```

**Intervals.icu translation:**
```
- 43m1s z2 pace

7x
- 17s z1 pace
```

> **Parser path:** same as 2026-03-20. Base run = 2700s − 7×17s = 2581s = 43m1s.
>
> **Known issue:** Same stride intensity issue as above (`z1` vs expected `z5`).

---

## 2026-03-29 | Brick Run Easy (30 min) — *Completed*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 30m z2 pace
```

> **Note:** No description — fallback to total duration at z2.

---

## 2026-03-31 | Easy Run (30 min) — *Planned*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 30m z2 pace
```

> **Note:** No description — fallback to total duration at z2.

---

## 2026-04-02 | Easy Run with Strides (45 min) — *Planned*

**FinalSurge description:**
```
Run 6-8 x 100m or 15-20s pickups, with full recovery
```

**Intervals.icu translation:**
```
- 43m1s z2 pace

7x
- 17s z1 pace
```

> **Parser path:** same as 2026-03-27.

---

## 2026-04-03 | Easy Run with Strides (30 min) — *Planned*

**FinalSurge description:**
```
Run 6-8 x 100m or 15-20s pickups, with full recovery
```

**Intervals.icu translation:**
```
- 28m1s z2 pace

7x
- 17s z1 pace
```

> **Parser path:** same as 2026-03-20.

---

## 2026-04-05 | Brick Run (45 min) — *Planned*

**FinalSurge description:**
```
15 mins easy + 2 x 10mins at HMP with 5 mins walk/easy jog rest + 5 mins easy
```

**Intervals.icu translation:**
```
- 15m z2 pace

2x
- 10m z4 pace
- 5m z2 pace
```

> **Parser path:** inline `Nx` (2x). Explicit warmup `15m easy` parsed from text before the `2 x`.
> Work = 10m @ HMP → `z4 pace`. Recovery = 5m walk/easy jog → `z2 pace`.
> Total: 15 + 2×(10+5) = 45 min ✓ — no remaining time for a separate cooldown step.
>
> **Translation quality: ✅ correct.** The "5 mins easy" at the end of the description
> is the recovery segment (matched by "with 5 mins walk/easy jog rest"), not a separate cooldown.

---

## 2026-04-07 | Easy Run (30 min) — *Planned*

**FinalSurge description:** *(none)*

**Intervals.icu translation:**
```
- 30m z2 pace
```

> **Note:** No description — fallback to total duration at z2.

---

## Summary

| Date | Name | Duration | Parser path | Quality |
|------|------|----------|-------------|---------|
| 2026-03-18 | Easy Run | 30 min | fallback (no desc) | — |
| 2026-03-20 | Easy Run with Strides | 30 min | inline Nx | ⚠️ stride intensity z1 vs z5 |
| 2026-03-24 | Easy Run | 30 min | fallback (no desc) | — |
| 2026-03-27 | Easy Run with Strides | 45 min | inline Nx | ⚠️ stride intensity z1 vs z5 |
| 2026-03-29 | Brick Run Easy | 30 min | fallback (no desc) | — |
| 2026-03-31 | Easy Run | 30 min | fallback (no desc) | — |
| 2026-04-02 | Easy Run with Strides | 45 min | inline Nx | ⚠️ stride intensity z1 vs z5 |
| 2026-04-03 | Easy Run with Strides | 30 min | inline Nx | ⚠️ stride intensity z1 vs z5 |
| 2026-04-05 | Brick Run | 45 min | inline Nx | ✅ correct |
| 2026-04-07 | Easy Run | 30 min | fallback (no desc) | — |

### Observations for Phase 5

1. **5 of 10 runs have no description** — post-race recovery period (race was 2026-02-01).
   These correctly fall back to `- Nm z2 pace`.

2. **Strides workout (4×):** The description `"Run 6-8 x 100m or 15-20s pickups, with full recovery"`
   is parsed correctly as 7×17s repeats, but the stride step maps to `z1 pace` instead of `z5 pace`
   because the intensity scanner hits `"recovery"` before `"pickups"` in the trailing clause.
   **Fix:** either add `"pickups"` → `z5 pace` to `INTENSITY_MAP`, or teach the scanner to
   prioritise the work segment text over the recovery clause.

3. **Brick Run (2026-04-05):** The bullet-list parser was **not** needed here (single prose line
   with `+` separators), but the inline `Nx` path handled it cleanly. The new bullet-list
   parser would fire on multi-bullet descriptions — confirmed working in the Phase-4 tests.

4. **No multi-bullet workouts** appeared in this window. The bullet-list parser is validated
   by unit tests against the `20-10-5` and `2×40min@MP` workout types from `workout_translations.md`.
