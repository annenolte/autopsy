# Scan time / cost normalization (reviewer #14)

The paper reported only aggregate scan time (~51s) and total API cost ($4–6).
The reviewer asked for time/cost **per KLOC, per file, per vulnerability**, and a
larger-codebase data point. The harness now records `target_loc`,
`scan_time_per_kloc`, and `scan_time_per_vuln` per run (in the results JSON and
the run report).

## Measured (frozen-protocol runs)

| target | LOC | scan time | time / KLOC | time / vuln |
|--------|-----|-----------|-------------|-------------|
| demo_project (single-shot) | 254 | 69.4 s | **273 s/KLOC** | 5.8 s/vuln |
| pygoat (chunked, ~8× larger) | 1,939 | 533 s | **275 s/KLOC** | 48.5 s/vuln |

Time per KLOC is essentially flat (~273–275 s/KLOC) from the 254-line demo to the
~8× larger pygoat app — a useful scaling data point: the chunked scanner keeps
throughput roughly linear in code size rather than blowing up.

## ⚠️ CAVEAT — cost (dollars) per KLOC is NOT reported
The Anthropic client in this repo does not capture per-call token usage, so the
harness cannot produce a dollar cost per KLOC / file / vuln. Only **time** is
normalized. A real cost-per-KLOC needs token accounting added to
`autopsy/llm/client.py` (future work). The ~$4–6 total figure from the paper
should be presented as an aggregate, not a normalized rate.
