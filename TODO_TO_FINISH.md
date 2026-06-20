# What's left to finish ALL reviewer requests

Everything that can be done in **code** is done (branch `repro-artifacts`).
What remains falls into 4 buckets: **(1) one paid run**, **(2) push the repo**,
**(3) paper writing — yours**, **(4) honest descoping for the few things that
can't be fully done.** Full per-item status is in `REVIEWER_RESPONSE.md`; the
numbers to cite are in `PAPER_HANDOFF.md`.

---

## BUCKET 1 — Run the one paid batch (~$20–25, or ~$10 minimal)
Closes the *staged* numbers. Commands (also in `PAPER_HANDOFF.md §9b`):
```bash
git clone https://github.com/adeyosemanputra/pygoat.git /tmp/pygoat
git clone https://github.com/s2e-lab/SecurityEval.git /tmp/SecurityEval

python benchmark/eval.py --arm all --repeat 5                               # demo: graph vs triage vs raw  -> #11, #16
python benchmark/eval.py --demo /tmp/pygoat/introduction \
  --ground-truth benchmark/pygoat/ground_truth_pygoat.json \
  --baseline-mode whole-file --chunked --arm both --repeat 5                # pygoat CI -> #2, #5, #13
python benchmark/eval.py --demo /tmp/SecurityEval/Testcases_Insecure_Code \
  --baseline-mode whole-file --chunked --arm both                          # SecurityEval LLM -> #2 (best new number)
python benchmark/eval.py --demo benchmark/js_demo \
  --ground-truth benchmark/js_demo/ground_truth_js.json \
  --baseline-mode whole-file --arm both --repeat 5                          # TypeScript -> #3
```
Minimal version ($10): just the **SecurityEval LLM** + **pygoat CI**.
This produces: established-benchmark numbers (#2), the triage ablation (#16),
multi-language numbers (#3), tight CIs + per-category + tokens/KLOC (#13/#14).

## BUCKET 2 — Publish (closes #20)
```bash
git checkout main && git merge repro-artifacts      # review first
git push origin main
git tag v1.0-paper && git push origin v1.0-paper    # frozen artifact for the paper
```

## BUCKET 3 — Paper writing (the bulk — only you can do this)
Each line = a reviewer item you close by writing, using results already in the repo:

- **#1** remove the numbered list → reflow into prose.
- **#4** delete/redo the IRIS "46% vs 91.67%" comparison — different dataset/lang; not comparable.
- **#5** report frozen-protocol numbers; label everything **pre-** vs **post-correction**; **drop "true recall 100%."** Replace 91.67% with the honest distribution (demo ~81% F1; pygoat 100% recall).
- **#6** write up the deletion experiment (2/2) **and** its over-fire limitation (`benchmark/deletion/`).
- **#7** scope the novelty to *diff-only added-line scanners*; add a related-work paragraph (code property graphs, taint analysis, dead/commented-code activation, review-evasion). Stop claiming "not previously described."
- **#8 / #9** **descope the AI-authorship detector**: present it as (a) reliable explicit-marker detection + (b) a soft prioritization heuristic, **not** a validated classifier (cite ROC-AUC 0.42 on unmarked code). Report vuln detection **separately** from authorship. (`AUTHORSHIP.md`)
- **#10** add a **Threat Model** section (attacker, deployment, in-scope vs out-of-scope vuln classes — raw material in `benchmark/pygoat/README.md`).
- **#12** describe the matching protocol (`FROZEN_PROTOCOL.md`).
- **#13** include the per-category table (`benchmark/per_category.py` output).
- **#14** report time/KLOC (~273–275 s/KLOC) + tokens/KLOC (`TIMING.md`); present $4–6 as an aggregate.
- **#15** write up the subgraph-cap study (`SUBGRAPH_CAPS.md`).
- **#17** cut the "Claude Security confirms significance" marketing line.
- **#18** report the Semgrep/Bandit comparison (`BASELINES.md`); **correct** the inaccurate claims (Semgrep *does* have cross-file taint).
- **#19** soften the grand tone; evidence is two repos + SecurityEval.
- **#21** expand the literature review to 25–30 peer-reviewed studies.
- **Minors 1–13 + formatting**: tone, split long sentences, define blast-radius/zero-footprint/triage/AST/BFS/REPL, add a block diagram (git diff→graph→Haiku→Sonnet), reformat Tables 1–2, cost model, trademark symbols, restate the 12 vulns in Results, condense the Anthropic-launch mentions, rename the last section "Conclusion". **Format: Times New Roman 12pt, bold headings, ≤20pp single / ≤40pp double.**

## BUCKET 4 — Can't be fully finished (handle honestly in the paper)
- **#2 (named C/Java benchmarks)**: CWE-Bench-Java is Java (tool is Python/JS/TS); Juliet is mostly C/Java; PrimeVul/ReposVul are large multi-language CVE sets = big future-work lift. You satisfied the *spirit* with SecurityEval (named, Python) + pygoat. State this and list the others as future work.
- **#9 (authorship)**: cannot be made a working classifier on unmarked code (signals are uninformative). Descope — don't claim it works.
- **#16 (prompt/model-version sensitivity)**: not built; list as future work (variance + triage ablation are done).
- **#18 (CodeQL)**: not run (heavy CLI, no package manager here). Semgrep+Bandit are your SAST baselines; cite CodeQL as future or run it manually.

---

## One-line summary
**Run one paid batch → push+tag → write the paper (descoping authorship, scoping
multi-language & novelty, adding threat model + literature) → list the 4
genuinely-out-of-reach items as future work.** That closes every reviewer
comment that *can* be closed, honestly.
