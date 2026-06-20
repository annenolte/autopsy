# Autopsy — Paper Handoff / Data & Changes Reference

Single-file reference of everything produced in the artifact-improvement work, so
it can be written up faithfully. **All numbers below are real and reproducible
from the repo; honest caveats are marked `⚠️ CAVEAT` and must survive into the
paper — do not drop them.** Branch: `repro-artifacts` (24 commits, not pushed).
Test suite: **63 passing**.

> Reporting rules that keep this defensible:
> - Report **mean ± std** over runs, not a single best run.
> - Round percentages to **whole numbers**.
> - **Recall** is the headline on incomplete-ground-truth targets; **do not claim
>   precision on pygoat** (its labels are incomplete by design).
> - Label every number as **pre-** or **post-protocol-freeze** (see below).
> - The old paper figures (91.67% P/R/F1, "true recall 100%") came from looser
>   scoring + a cherry-picked run; they should be replaced with the numbers here.

---

## 1. What the tool is

Autopsy detects vulnerabilities in AI-generated / AI-modified code. Components:
- **Tree-sitter parser** (Python, JS, TS, TSX) → **NetworkX dependency graph**
  (function/class/file nodes; `imports`, `calls`, `contains` edges).
- **AI-authorship heuristic** (7 weighted signals) to prioritize likely-AI code.
- **Two-stage LLM pipeline**: Claude Haiku (triage) → Claude Sonnet (analysis).
- **Deletion / "zero-footprint" detector**: comment-boundary deletions +
  pre/post graph-diff for removed security controls.
- **Deterministic AST/graph detectors** (added this session): ignored
  security-gate returns, SQL string-injection sinks, weak hashing.
- **Map-reduce "chunked" scanner** (added this session): windows large files so
  nothing past the old 500-line truncation is dropped.

### Models (frozen)
- Triage: `claude-haiku-4-5-20251001`
- Analysis: `claude-sonnet-4-5-20250929`
- ⚠️ CAVEAT: the model the paper originally used, `claude-sonnet-4-20250514`,
  was **retired by Anthropic (404)**; we pinned the successor. Absolute numbers
  differ from the original model. Note this in the paper.

---

## 2. Frozen evaluation protocol

Locked before the final rerun (commit `6da8b87`), no post-hoc edits after.
A finding matches a ground-truth entry iff:
1. **file basename** matches, AND
2. **category** matches after normalization (generic "Injection" bridges to the
   injection family; entries may list `accepted_categories`), AND
3. reported **line within ±5** (`--fuzz-lines`, default 5) of `[line_start, line_end]`.

Matching is **one-to-one**, ties broken by smallest line distance. Findings at
the same file within 3 lines with overlapping category are **deduped** before
scoring. Provisional ground-truth entries are excluded unless `--include-provisional`.

⚠️ CAVEAT (must state): the matcher was developed partly by inspecting the demo
and pygoat outputs, so the frozen rerun is a **reproduction under a locked
protocol, not a blind test**. A genuinely blind number needs a fresh target
(e.g. the TypeScript LLM run, not yet executed).

---

## 3. Benchmarks (all in `benchmark/`)

| benchmark | what | # planted vulns | ground truth |
|-----------|------|-----------------|--------------|
| `demo_project/` | synthetic Flask user-mgmt app (the paper's original benchmark) | 12 (+1 provisional) | `benchmark/ground_truth.json` |
| `benchmark/baseline/` | **reconstructed** safe version of the demo (the "before" diff state) | — | — |
| `benchmark/pygoat/` | **real third-party** OWASP pygoat (Django), external validation | 11 in-scope | `benchmark/pygoat/ground_truth_pygoat.json` |
| `benchmark/deletion/` | deletion-/comment-activation vulns | 2 | `benchmark/deletion/ground_truth_deletion.json` |
| `benchmark/js_demo/` | TypeScript Express app (multi-language) | 8 | `benchmark/js_demo/ground_truth_js.json` |
| `benchmark/heldout/` | "orders" generality fixture (vulnerable + safe) | 3 | — |

- pygoat provenance: `github.com/adeyosemanputra/pygoat` @ `19d17cc8` (not vendored).
- pygoat in-scope = code-level vulns only (2× SQLi, pickle + YAML deserialization,
  command injection, eval + ImageMath code injection, SSRF, MD5, XXE, SSTI).
  Out-of-scope (excluded, documented): broken access control, security
  misconfig, vulnerable components, insufficient logging.

---

## 4. RESULTS

### 4.1 Demo — Autopsy, frozen matcher (re-scored offline from saved runs)
| scenario | N | Precision | Recall | F1 |
|----------|---|-----------|--------|----|
| whole-file | 9 | 87% ± 6 (max 100%) | 76% ± 10 (max 92%) | **81% ± 5 (max 88%)** |
| safe (frozen rerun) | 1 | 83% | 83% | 83% |

Per-run F1 (whole-file): 73, 76, 76, 80, 82, 82, 83, 85, 88.
⚠️ CAVEAT: this **replaces** the paper's 91.67%; that figure was looser scoring +
best-run cherry-pick. Report the distribution.

### 4.2 Ablation — Autopsy (full pipeline) vs Raw Sonnet (no graph)
Same model, same prompt, same scorer; only the graph pipeline differs.
| benchmark | Autopsy recall | Raw Sonnet recall |
|-----------|----------------|-------------------|
| pygoat (frozen, 11 in-scope) | **100% (11/11)** | 45% (5/11) |
| pygoat (pre-freeze 4-run CI) | 100% (11/11 every run) | ~57% (7,7,5,6/11) |
| demo (frozen safe, single) | 83% F1 | 76% F1 (R 67%) |

This is the central "does the architecture help?" result: on the external app,
Autopsy recalls every in-scope vuln; raw single-prompt LLM gets ~half.

### 4.3 SAST baselines — Semgrep & Bandit (same matcher) — reviewer #18
| target | Autopsy | Semgrep | Bandit |
|--------|---------|---------|--------|
| pygoat (recall, 11) | **100%** | 64% (7/11) | 45% strict / 82% loc-only (5–9/11) |
| demo (recall/F1, 12) | ~76–83% | 25% (3/12) | 42% (5/12) |
⚠️ CAVEAT: **recall only.** Precision not compared (pygoat GT incomplete; Bandit
emitted 36 findings = noisy). Semgrep `p/python` is the standard config, not
Semgrep Pro (which has interfile taint). CodeQL not run (commands documented).

### 4.4 Deletion / zero-footprint detector — reviewer #6
- Recall: **2/2** planted deletion vulns (comment-boundary activation +
  security-control deletion), deterministically, no LLM.
- ⚠️ CAVEAT: the comment-boundary detector **over-fires** — it flags any deleted
  `"""`, including a benign docstring on a removed function (a false positive).
  Report this limitation.

### 4.5 AI-authorship heuristic — false-positive rate — reviewer #8/#9
Run over real **pre-2021 (human-era)** commits; every flag is a false positive.
| corpus | human .py files | FP (as-shipped) | FP (code-only) |
|--------|-----------------|-----------------|----------------|
| requests | 455 | 3% | 9% |
| flask | 817 | 2% | 6% |
| **combined** | **1272** | **~2%** | **~7%** |
FP drivers: `bulk_addition`, `boilerplate_density`, `complete_functions`.
⚠️ CAVEAT: this is **only the FP-on-human half**. Full precision/recall/AUC needs
a labeled AI-positive set we did not have and did not fabricate. Present the
heuristic as a *prioritization hint with a measured ~2% human FP rate*, not a
validated classifier. Also report vuln-detection separately from authorship.

### 4.6 Subgraph depth/node-cap study — reviewer #15
| repo | % neighborhoods > 50 nodes @ depth5 | % chains > 5 hops (max) |
|------|-------------------------------------|-------------------------|
| demo | 0% | 0% (2) |
| pygoat | 4% | 0% (1) |
| requests | **13%** | **9% (6)** |
| flask | 4% | 4% (8) |
| autopsy | 4% | 4% (8) |
Median node fits the caps; a real minority (5–13% of neighborhoods, 4–9% of
chains, depth up to 8) exceeds them on mature libraries → caps can truncate and
hide deep cross-file bugs. The `--chunked` scanner fixes *file-line* truncation
but not this; adaptive caps are future work.

### 4.7 Per-category recall — reviewer #13
On pygoat, every category caught: SQLi 2/2, Code Injection 2/2, Insecure
Deserialization 2/2, Command Injection 1/1, SSRF 1/1, SSTI 1/1, Weak Crypto 1/1,
XXE 1/1.

### 4.8 Multi-language (TypeScript) — reviewer #3
- Built a cross-file TS Express benchmark (8 vulns).
- **Fixed a real parser bug**: exported TS functions (under `export_statement`)
  weren't extracted → empty graph for idiomatic TS. After fix, `runQuery`,
  `isAuthorized`, `hashPassword` extract.
- Semgrep (`p/default`) on the TS app: **4/8 strict, 6/8 loc-only**.
- ⚠️ CAVEAT (important): even after the fix, **anonymous Express route handlers
  and cross-file call edges are not captured**, so Autopsy's graph mechanism is
  Python-centric and only partial for idiomatic JS/TS. **Scope the
  multi-language claim** accordingly. The Autopsy LLM scan on TS was not run
  (needs tokens).

---

## 5. Code changes / new artifacts (24 commits, branch `repro-artifacts`)

Tool changes (`autopsy/`):
- `llm/client.py` — pinned Sonnet model to available successor.
- `detection/ignored_returns.py` — NEW deterministic cross-file ignored-auth-gate detector.
- `detection/static_rules.py` — NEW deterministic SQL-string-injection + weak-hash detectors.
- `llm/pipeline.py` — wire deterministic detectors into the scan; dedup hint to the LLM.
- `llm/chunking.py` — NEW map-reduce chunked scanner.
- `parser/extractors.py` — FIX: extract exported JS/TS functions (`_unwrapped_children`).

Benchmark/harness (`benchmark/`): `eval.py` (matcher, dedupe, `--arm` ablation,
`--baseline-mode`, `--chunked`, `--ground-truth`, `--repeat` mean/std),
`make_diff.py`, `compare_tools.py` (Semgrep/Bandit), `eval_deletions.py`,
`eval_authorship.py`, `eval_subgraph_caps.py`, `per_category.py`,
`validate_heldout.py`, plus ground-truth JSONs and per-experiment READMEs
(`README.md`, `BASELINES.md`, `AUTHORSHIP.md`, `SUBGRAPH_CAPS.md`,
`FROZEN_PROTOCOL.md`, `pygoat/README.md`, `deletion/README.md`,
`js_demo/README.md`, `heldout/README.md`).

Docs: `REVIEWER_RESPONSE.md` (point-by-point status of every reviewer comment),
`PAPER_HANDOFF.md` (this file).

Full commit list: `git log --oneline main..repro-artifacts`.

---

## 6. Tests (63 passing)
| file | tests | covers |
|------|-------|--------|
| test_parser.py | 7 | tree-sitter parsing |
| test_graph.py | 8 | dependency graph |
| test_heuristics.py | 17 | authorship signals |
| test_deletions.py | 3 | comment-boundary detection |
| test_api.py | 6 | server API |
| test_detectors.py | 6 | deterministic detectors (+ held-out generality, no-FP-on-safe) |
| test_eval_dedupe.py | 3 | finding dedupe |
| test_chunking.py | 3 | map-reduce window coverage |
| test_deletion_benchmark.py | 3 | deletion benchmark + documented over-fire |
| test_authorship_heuristic.py | 3 | authorship discrimination |
| test_subgraph_caps.py | 2 | cap-study helpers |
| test_js_extraction.py | 2 | exported TS function extraction (the fix) |

---

## 7. Reviewer comments — status
See `REVIEWER_RESPONSE.md` for the full point-by-point matrix. Summary:
- **Addressed in artifact:** #6, #11, #12, #13, #15, #18, #20, minor #3.
- **Partial (real progress + honest gaps):** #2, #3, #5, #8, #9, #14, #16.
- **Paper-writing only (not done — your task):** #1, #4, #7, #10, #17, #19, #21,
  most minors (threat model, literature review of 25–30 studies, tone,
  formatting: Times New Roman 12pt, ≤20pp single / ≤40pp double).

---

## 8. Reproduction commands
```bash
pip install -e ".[dev]" && pip install semgrep bandit   # semgrep may be a separate venv (click conflict)
export ANTHROPIC_API_KEY=sk-...

# Main eval (demo): ablation, mean/std
python benchmark/eval.py --arm both --repeat 5
python benchmark/eval.py --baseline-mode whole-file --arm both --repeat 5

# External benchmark (pygoat): clone first, then chunked
git clone https://github.com/adeyosemanputra/pygoat.git /tmp/pygoat
python benchmark/eval.py --demo /tmp/pygoat/introduction \
  --ground-truth benchmark/pygoat/ground_truth_pygoat.json \
  --baseline-mode whole-file --chunked --arm both --repeat 5

# Deterministic experiments (no API):
python benchmark/eval_deletions.py
python benchmark/validate_heldout.py
python benchmark/eval_subgraph_caps.py --repo <any repo>
python benchmark/eval_authorship.py --repo <human repo> --before 2021-01-01 --max-commits 2500 --min-added 20
python benchmark/compare_tools.py --target demo_project --ground-truth benchmark/ground_truth.json
python benchmark/per_category.py --results <results.json> --ground-truth <gt.json>
```

---

## 9b. Additional experiments (#9, #2, #16) — added after the first handoff

### #9 — AI-authorship heuristic validated; one real bug fixed; split result
Labeled set from **SecurityEval**: 260 AI files (Copilot+InCoder) vs 121 human.
- **Bug found + fixed:** an explicit `Co-Authored-By: Claude/Copilot/Cursor`
  trailer scored the commit_message signal 1.0 but the weighted-AVERAGE diluted
  it to ~0.15, so marked AI code was scored not-AI. Now explicit markers are
  **decisive** (`likely_ai`); verified, and human false-positive rate unchanged
  (~2%). So **marked AI code is now reliably flagged.**
- **Unmarked AI code: still not separable** — content signals are near-random on
  the snippets (ROC-AUC 0.42; per-signal AUC 0.41–0.52).
⚠️ **Paper framing:** marker detection + soft prioritization, **not** a general
classifier of unmarked AI code; report vuln-detection separately from authorship.
(`benchmark/eval_authorship_classifier.py`, `AUTHORSHIP.md`.)

### #2 — Established benchmark: SecurityEval (121 CWE-labeled files)
Now on TWO external benchmarks (pygoat + SecurityEval). Token-free baselines on
SecurityEval (per-file detection = recall): Autopsy-deterministic **3%**, Semgrep
**19%**, Bandit **40%**. ⚠️ The **Autopsy LLM number on SecurityEval is NOT yet
measured** (staged, needs tokens). SecurityEval is hard for SAST (69 diverse
CWEs) — expected. (`benchmark/eval_securityeval.py`, `SECURITYEVAL.md`.)

### #16 — Sonnet-only vs Haiku+Sonnet ablation (built, staged)
`scan_stream(use_triage=False)` + `--arm sonnet-only` / `--arm all`
(autopsy vs sonnet-only vs raw) isolate whether the Haiku triage step helps.
Code is built and tested; ⚠️ **the comparison run needs tokens** (staged).

### Updated one-time paid batch (buy ~$25 for margin)
```bash
python benchmark/eval.py --arm all --repeat 5                              # demo: graph vs triage vs raw (#11,#16)
python benchmark/eval.py --demo /tmp/pygoat/introduction \
  --ground-truth benchmark/pygoat/ground_truth_pygoat.json \
  --baseline-mode whole-file --chunked --arm both --repeat 5               # pygoat CI
python benchmark/eval.py --demo /tmp/SecurityEval/Testcases_Insecure_Code \
  --baseline-mode whole-file --chunked --arm both                          # SecurityEval Autopsy LLM (#2)
```

## 9. Not done / needs tokens (be explicit in the paper)
- Truly-blind run on a fresh target (TS LLM scan); larger CIs.
- Established benchmarks the reviewer named (CWE-Bench-Java [Java, unsupported],
  SecurityEval, Juliet, PrimeVul, ReposVul) — pygoat is the external stand-in.
- AI-positive labeled set for full authorship classifier P/R/AUC.
- Cost-per-KLOC/vuln (client doesn't capture token usage).
- All paper prose, threat model, literature review, formatting.
