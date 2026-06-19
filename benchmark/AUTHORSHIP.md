# AI-authorship heuristic: false-positive measurement (reviewer #8/#9)

The reviewer noted the 7-signal authorship heuristic uses hand-tuned weights,
was validated only anecdotally, and likely fires on ordinary human code. The
most important, checkable part of that is the **false-positive rate on human
code**, which `benchmark/eval_authorship.py` measures directly — no LLM.

## Method
Run the heuristic over real `.py` commits (≥20 added lines) from two mature
libraries' **pre-2021 history** (before AI coding assistants were in wide use),
so every "likely AI" flag is a false positive. Two rates: as-shipped (includes
the commit-message signal) and code-only (signal removed).

```bash
python benchmark/eval_authorship.py --repo /tmp/requests_human --before 2021-01-01 --max-commits 2500 --min-added 20
python benchmark/eval_authorship.py --repo /tmp/flask_human    --before 2021-01-01 --max-commits 2500 --min-added 20
```

## Result

| corpus | human .py files | FP (as-shipped) | FP (code-only) |
|--------|-----------------|-----------------|----------------|
| requests (pre-2021) | 455 | 3% (15) | 9% (42) |
| flask (pre-2021)    | 817 | 2% (16) | 6% (51) |
| **combined**        | **1272** | **~2% (31)** | **~7% (93)** |

FP drivers: `bulk_addition`, `boilerplate_density`, `complete_functions` — i.e.
large human feature commits with docstrings and several functions look "AI-ish."

## Honest reading
- **Good news for the tool:** at the 0.5 threshold the heuristic is fairly
  conservative on human code (~2% as-shipped), *not* the rampant over-flagging
  the reviewer (and we) expected. That's a real, defensible number on 1.3k files.
- **Design quirk:** the commit-message signal, when it scores low, *lowers*
  overall confidence (it adds weight to the denominator). So removing it
  *raises* the FP rate (9%/6%). The confidence math conflates "no AI signal"
  with "evidence against AI." Worth fixing.
- **This is only half the validation.** It measures false positives on human
  code. It does **not** measure whether the heuristic correctly identifies *AI*
  code (recall / precision / AUC), because that needs a labeled AI-vs-human
  commit set we did not have and would not fabricate. Until that exists, the
  heuristic should be presented as a **prioritization hint with a measured ~2%
  human FP rate**, not a validated classifier — and vulnerability-detection
  results should be reported separately from authorship (as the reviewer asked).
- **Weights not retrained.** The reviewer asked to calibrate/train the weights;
  doing that properly also needs the AI-positive set, so it is left as future
  work rather than tuned blindly.
