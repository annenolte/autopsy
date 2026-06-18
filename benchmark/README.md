# Autopsy evaluation benchmark

Frozen artifacts for reproducing the paper's evaluation. See the
"Reproduce the evaluation" section of the top-level `readme.md` for setup and
run commands. This file documents the artifacts and, importantly, what is
reconstructed.

## Contents

| Path | What it is |
|------|------------|
| `ground_truth.json` | Authoritative list of planted vulnerabilities with line ranges read directly from `demo_project/`. |
| `baseline/` | **Reconstructed** clean ("before") version of the demo module. |
| `make_diff.py` | Builds a 2-commit temp git repo (baseline → vulnerable) and emits the unified diff, mirroring `autopsy scan`. |
| `eval.py` | Runs the scan against the diff, parses findings, matches them to ground truth, and reports precision / recall / F1. |
| `results/` | Per-run JSON output (gitignored). |

The scan target itself is `demo_project/` at the repository root (the
"after"/vulnerable state).

## Matching rule

A streamed finding matches a ground-truth entry when **all** hold:

1. file basename matches,
2. normalized category matches (e.g. ground-truth `Weak Crypto` ↔ the scanner's
   `Secrets Exposure` wording — see `normalize_category` in `eval.py`),
3. the reported line is within `--fuzz-lines` (default **5**) of
   `[line_start, line_end]`.

Matching is one-to-one (a finding can satisfy at most one entry and vice versa);
ties break by smallest line distance. `--fuzz-lines 25` reproduces the looser
tolerance used during development.

## ⚠️ Reconstruction notice (please confirm)

- **`baseline/` is a reconstruction, not recovered source.** No
  pre-vulnerability version of `demo_project/` was ever committed, so the safe
  baseline was rebuilt from the vulnerable files: same module structure and
  function signatures, vulnerabilities removed. Each baseline file says so in
  its header. `baseline/routes.py` is byte-identical to the demo (it has no
  planted vulnerability), so it produces no diff.

- **`sqli-search-service` is a provisional 13th entry (please confirm).**
  `demo_project/user_service.py` `search_users` (lines 10–14) forwards the
  unvalidated `query` argument into `build_search_query` → `execute_read` — a
  genuine SQL-injection forwarding sink that the labeled set omitted, and one
  Autopsy flagged repeatedly in development runs. It is marked
  `"provisional": true` in `ground_truth.json` and is **excluded from scoring by
  default**; pass `--include-provisional` to score it. The headline metric stays
  on the 12 authoritative planted vulnerabilities until this is confirmed.

## Determinism

The scan uses Claude's default sampling — the current client
(`autopsy/llm/client.py`) exposes no temperature parameter, and the harness does
not change the tool's detection path to add one. Results therefore vary slightly
between runs; use `--repeat N` to report mean ± standard deviation.

**Model substitution (2026-06-18).** The analysis model used when the paper was
written, `claude-sonnet-4-20250514`, has been retired by Anthropic and now
returns a 404, which broke the live benchmark. The client is pinned to its
date-stamped successor, `claude-sonnet-4-5-20250929` (see the note in
`autopsy/llm/client.py`); the triage model `claude-haiku-4-5-20251001` is
unchanged and still available. Absolute precision/recall therefore differ from
the original model — confirm whether you want this successor pinned for the
camera-ready, or a different available model.

> Install Autopsy editable from this repo (`pip install -e .`) before running the
> benchmark, so `import autopsy` resolves to this code and not another local
> checkout.
