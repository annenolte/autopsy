# External validation target: OWASP pygoat

[pygoat](https://github.com/adeyosemanputra/pygoat) is a real, third-party,
intentionally-vulnerable Django application. Using it as an *external* benchmark
is far more credible than the in-repo `demo_project/`, because it was written by
someone else, for a different purpose, and it covers diverse vulnerability
shapes. **pygoat is not vendored here** — clone it yourself; `ground_truth_pygoat.json`
only references line numbers.

Provenance: `github.com/adeyosemanputra/pygoat` @ `19d17cc8` (2026-03-28).

## Ground truth (8 verified, code-level vulnerabilities)

Each was confirmed by reading `introduction/views.py` and checking that user
input reaches the sink:

| id | category | function | sink line |
|----|----------|----------|-----------|
| pygoat-sqli-login | SQLi | `sql_lab` | 162 (`.raw()`, concat) |
| pygoat-insecure-deser-pickle | Insecure Deserialization | `insec_des_lab` | 214 (`pickle.loads` of cookie) |
| pygoat-command-injection | Command Injection | `cmd_lab` | 430 (`Popen(shell=True)`) |
| pygoat-code-injection-eval | Code Injection | `cmd_lab2` | 460 (`eval`) |
| pygoat-unsafe-yaml | Insecure Deserialization | `a9_lab` | 560 (`yaml.load`+`Loader`) |
| pygoat-sqli-injection-lab | SQLi | `injection_sql_lab` | 878 (`.raw()`, concat) |
| pygoat-ssrf | SSRF | `ssrf_lab2` | 963 (`requests.get`) |
| pygoat-weak-hash | Weak Crypto | `crypto_failure_lab` | 1026 (`md5`) |

**Deliberately excluded** (not statically decidable / out of Autopsy's scope, so
not guessed): security misconfiguration, vulnerable components, business-logic
access-control. The SSTI lab's `os.path.join` uses a server-generated UUID (not
user input), so it is **not** path traversal and was excluded.

## What we already learned for free (no API)

Running just the deterministic layer (no LLM) against pygoat:

```
TP=1 FP=2 FN=7  →  recall 12%, precision 33%   (caught: weak-hash only)
```

This is an honest and important result: the current static rules were shaped
around `demo_project`'s patterns (f-string → known wrapper sink, md5,
ignored-return). pygoat uses *different* shapes — string **concatenation** into
Django `.raw()`, `subprocess(shell=True)`, `eval`, `pickle`, `yaml`,
`requests.get` — that the narrow rules don't cover, and the broad `verify`/`md5`
keywords produced 2 false positives. **Takeaway:** on diverse real code the LLM's
generality carries recall; the deterministic layer must be broadened (covering
more sink/taint shapes) to keep up. That broadening should be validated on the
in-repo held-out fixture, **not** tuned to pygoat — pygoat must stay an unbiased
external test.

## Running the full pipeline (costs API tokens)

```bash
git clone https://github.com/adeyosemanputra/pygoat.git /tmp/pygoat
python benchmark/eval.py \
  --demo /tmp/pygoat/introduction \
  --ground-truth benchmark/pygoat/ground_truth_pygoat.json \
  --baseline-mode whole-file --arm both --repeat 3
```

> **Caveat — do this AFTER map-reduce.** `introduction/views.py` is ~1,240 lines
> and the scan context truncates files past 500 lines, so most pygoat vulns
> (lines 855–1026) would be cut off and a live run now would under-report due to
> truncation, not capability. Build the chunked/map-reduce scanner first, then
> this number is meaningful.

## Comparison baselines (other tools)

Run mature scanners on the same code for a tools-comparison table (they are
*baselines*, not ground truth):

```bash
pip install bandit semgrep
bandit -r /tmp/pygoat/introduction -f json -o bandit_pygoat.json
semgrep --config p/python --json -o semgrep_pygoat.json /tmp/pygoat/introduction
```
