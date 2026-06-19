# Reviewer response matrix — Autopsy

Status of each reviewer comment. **Legend:**
- ✅ **Done (artifact)** — handled in the code/benchmark; still must be *written into the paper*.
- 🟡 **Partial** — started, but not fully meeting what the reviewer asked.
- ❌ **Code/experiment TODO** — needs new code or a new experiment.
- ✍️ **Paper TODO** — writing/framing/literature only; no code involved.

> Reality check: the reviewer reviews the *manuscript*. Even ✅ items don't count
> until the numbers, tables, and claims are rewritten to match the artifact.

## Major issues

| # | Topic | Status | What's left |
|---|-------|--------|-------------|
| 1 | Remove numbered points | ✍️ Paper TODO | Reflow the numbered list into prose. |
| 2 | Tiny benchmark; use an established benchmark + frozen repo + **pre-registered matching protocol fixed before scoring** | 🟡 Partial | Added pygoat (real third-party app) with frozen labels + reproducible harness. **But** pygoat is not one of the named benchmarks (CWE-Bench-Java, SecurityEval, Juliet, PrimeVul, ReposVul), it's one app, and our matcher was tuned *after* seeing results. To satisfy: evaluate on ≥1 named benchmark, and **freeze the protocol, then run blind**. |
| 3 | Multi-language claim but only Python/Flask tested | ❌ Code/experiment TODO | Build a JS/TS (and ideally one more) benchmark and report it. Currently 100% Python. |
| 4 | Unfair IRIS+GPT-4 (46% on CWE-Bench-Java) comparison | ✍️ Paper TODO | Remove or explicitly reframe as not-comparable (different dataset/language/difficulty). |
| 5 | Don't self-adjudicate 1 FN/1 FP; repair GT+matching, freeze, rerun; label pre/post; don't co-report 91.67% and 100% | 🟡 Partial | GT + matching repaired and rerun; whole-number rounding. **Still:** stop reporting "true recall 100%"; freeze protocol and rerun blind; label every number pre- or post-correction. |
| 6 | Deletion / comment-activation is core novelty but **no benchmark vuln tests it** | ✅ Done (artifact) | `benchmark/deletion/` adds 2 deletion-based vulns (comment activation + security-control deletion); `eval_deletions.py` measures the detectors (2/2 recall, no LLM). Honestly documented limitation: the comment detector over-fires on benign docstring deletions. Write this experiment + limitation into the paper. |
| 7 | Novelty claim unsupported / "additions-only" false at field level | ✍️ Paper TODO | Do a literature search; scope novelty to *diff-only added-line scanners*; discuss CPGs, taint, semantic diffs, dead-code activation, supply-chain/review-evasion. |
| 8 | 7-signal authorship heuristic: hand weights, anecdotal validation, fires on human code | ❌ Code/experiment TODO | Calibrate/train on a labeled authorship dataset; report FP rate on human/templated/generated/refactor commits. Untouched. |
| 9 | Is benchmark code actually AI-generated? Authorship detector never validated | ❌ Code/experiment TODO | Build a labeled AI-vs-human commit set; report classifier precision/recall/AUC; report vuln-detection separately from authorship. Untouched. |
| 10 | No explicit threat model | ✍️ Paper TODO | Write a threat-model section (attackers, deployment, in-scope vs out-of-scope vuln classes). Raw material exists in benchmark/pygoat scope notes. |
| 11 | Only end-to-end eval; no ablation | ✅ Done (artifact) | `--arm raw` (Sonnet, no graph) vs `--arm autopsy` ablation exists. Still need: write it up; ideally also Haiku+Sonnet vs Sonnet-only and authorship-on/off ablations. |
| 12 | Matching coarse (basename + FUZZ=25), mis-matched weak-hash | ✅ Done (artifact) | Default fuzz 5, one-to-one matching, category gating, dedupe, `--fuzz-lines`. Write up the protocol. |
| 13 | Only overall TP/FP/F1; no per-category | 🟡 Partial | Per-finding category data is in results JSON; add a per-category results table. |
| 14 | No cost/time per KLOC/file/vuln; no scaling experiment | 🟡 Partial | Chunked scanner + pygoat run exist; compute and report per-KLOC / per-file / per-vuln cost and a larger-repo scaling curve. |
| 15 | depth-5 / 50-node subgraph cap not empirically tested | ❌ Code/experiment TODO | Measure real cross-file chain lengths vs the caps; show miss rate. (Chunking mitigates file truncation but not this.) |
| 16 | 5 runs, only final reported; no variance / prompt / model / Haiku-vs-Sonnet sensitivity | 🟡 Partial | `--repeat` gives mean±std (variance ✅). Still need prompt-sensitivity, model-version, and Sonnet-only ablations. |
| 17 | "Claude Security confirms significance" = marketing | ✍️ Paper TODO | Remove or replace with a technical comparison. |
| 18 | Run Semgrep/CodeQL on the same benchmark; fix inaccurate capability claims | ✅ Mostly done | Semgrep + Bandit now run on both benchmarks via `benchmark/compare_tools.py`; results in `benchmark/BASELINES.md` (pygoat recall: Autopsy 100% vs Semgrep 64% vs Bandit 45/82%; raw-LLM 57%). **Still:** run CodeQL (commands in compare_tools.py), and correct the Semgrep cross-file capability claims in the paper text. |
| 19 | Tone too grand for one repo | ✍️ Paper TODO | Soften claims; pygoat adds a second repo but evidence is still limited. |
| 20 | Publish benchmark code, diffs, prompts, configs | ✅ Done (artifact) | All in `benchmark/` + prompts in `autopsy/llm/prompts.py`, pinned model IDs. **Still need to push the branch / release it.** |
| 21 | Literature review too thin (11 studies) | ✍️ Paper TODO | Expand to 25–30 peer-reviewed primary studies. |

## Minor issues

| # | Topic | Status |
|---|-------|--------|
| 1 | "ludicrous speed" etc. too casual | ✍️ Paper TODO |
| 2 | Long multi-clause sentences | ✍️ Paper TODO |
| 3 | Two-decimal % on 12 samples | ✅ Done (we round to whole %) — apply in paper |
| 4 | Define "blast radius/zero-footprint/triage" | ✍️ Paper TODO |
| 5 | Add a block diagram (git diff→graph→Haiku→Sonnet) | ✍️ Paper TODO |
| 6 | Define AST/BFS/REPL on first use | ✍️ Paper TODO |
| 7 | Dense Tables 1 & 2 | ✍️ Paper TODO |
| 8 | Casual example wording | ✍️ Paper TODO |
| 9 | "$0.50/day" vs "$4–6 total" inconsistent | ✍️ Paper TODO (give a per-scan / per-K-token model) |
| 10 | Trademark symbols for product names | ✍️ Paper TODO |
| 11 | Restate the 12 vulns in Results text | ✍️ Paper TODO |
| 12 | Anthropic launch mentioned 3× | ✍️ Paper TODO |
| 13 | Rename reflective last section to "Conclusion" | ✍️ Paper TODO |

## Formatting
Times New Roman 12pt, bold headings; ≤20 pages single-spaced / ≤40 double. — ✍️ Paper TODO.

## Suggested order to finish (highest leverage first)

1. **Freeze the matching protocol and rerun blind** (#2, #5) — protects every number you report. *Mostly done; needs a clean final run.*
2. **Run Semgrep + CodeQL on the benchmark** (#18) — cheap, concrete, and directly answers "is the architecture needed."
3. **Add deletion/comment-activation cases to the benchmark + measure** (#6) — backs your headline novelty with experiments.
4. **Validate the AI-authorship heuristic on a labeled set, or cut it** (#8, #9) — if you can't validate it, descope it from the paper.
5. **A JS/TS benchmark** (#3) — supports the multi-language claim or scope it down.
6. **Paper rewrite** (#1, #4, #7, #10, #17, #19, #21, all minors) — tone, threat model, literature, claims, formatting.

Items 2–5 are the experiments; everything in §"Paper TODO" is writing only.
