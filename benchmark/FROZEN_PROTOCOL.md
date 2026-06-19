# Frozen evaluation protocol (reviewer #2 / #5)

This protocol is **frozen as of this commit**. The reruns reported below were
executed *after* this file was committed, and the matcher, ground truth, and
config were **not** changed afterward regardless of the results. This is the
discipline the reviewer asked for ("fix the protocol, then rerun").

**Honesty caveat:** this is a *frozen-protocol reproduction*, not a blind test.
The matcher was developed partly by inspecting these same targets (demo_project
and pygoat), so this confirms the numbers are *stable under a locked protocol* —
it does not establish performance on unseen data. A genuinely blind number
requires a fresh target the protocol never saw (e.g. the TypeScript LLM run,
not yet executed).

## Frozen components
- **Matcher** (`benchmark/eval.py`): a finding matches a ground-truth entry iff
  file basename matches AND normalized category matches (with the generic
  "injection" bridge and per-entry `accepted_categories`) AND the reported line
  is within **fuzz = 5** of `[line_start, line_end]`. One-to-one assignment,
  ties broken by smallest line distance.
- **Dedupe**: findings at the same file + within 3 lines with overlapping
  category are merged before scoring (on by default).
- **Provisional** ground-truth entries excluded from scoring.
- **Models**: `claude-haiku-4-5-20251001` (triage), `claude-sonnet-4-5-20250929`
  (analysis).
- **Configs**:
  - demo_project: `--baseline-mode safe` (reconstructed clean baseline), single-shot.
  - pygoat: `--baseline-mode whole-file --chunked`, 11 in-scope vulns.
- **Reporting**: whole-number percentages; mean ± std over repeats; recall is the
  headline (precision not claimed on pygoat — incomplete labels).

## Results (filled from the frozen rerun)
See `benchmark/results/` JSON written by the rerun and the summary recorded in
the commit that follows this one. Numbers are reported as produced, with no
post-hoc matcher/GT edits.
