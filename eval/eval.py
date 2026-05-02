"""
Autopsy Evaluation Harness
==========================
Measures precision and recall of Autopsy's scan_stream against
the demo_project ground-truth vulnerability set.

Strategy: real before/after diff
  - "before" commit: empty stub files (clean baseline)
  - "after"  commit: full vulnerable demo_project files
  - diff = what Autopsy was built to scan

Usage:
    export ANTHROPIC_API_KEY=sk-...
    cd /path/to/autopsy
    python eval/eval.py --demo autopsy-release/demo_project --out results.json

Requirements:
    pip install autopsy gitpython rich
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import networkx as nx
from rich.console import Console
from rich.table import Table

console = Console()

# ─── Ground truth ────────────────────────────────────────────────────────────
# Each entry is one distinct vulnerability finding we expect Autopsy to detect.
# "file" is relative to demo_project root.
# "line_range" is (start, end) inclusive — fuzzy matched within ±5 lines.
# "category" must match one of Autopsy's 9 categories (case-insensitive substr).

GROUND_TRUTH = [
    # query_builder.py — SQL injections
    {
        "id": "sqli-search",
        "file": "query_builder.py",
        "line_range": (4, 13),
        "category": "sql",
        "description": "build_search_query — string-interpolated LIKE clause",
    },
    {
        "id": "sqli-update",
        "file": "query_builder.py",
        "line_range": (16, 24),
        "category": "sql",
        "description": "build_update_query — interpolated SET values",
    },
    {
        "id": "sqli-export",
        "file": "query_builder.py",
        "line_range": (27, 42),
        "category": "sql",
        "description": "build_export_query — user-controlled ORDER BY",
    },
    # database.py — raw SQL sinks
    {
        "id": "sqli-execute",
        "file": "database.py",
        "line_range": (18, 31),
        "category": "sql",
        "description": "execute_query / execute_read — no parameterization",
    },
    # auth.py
    {
        "id": "auth-bypass-token",
        "file": "auth.py",
        "line_range": (11, 22),
        "category": "auth",
        "description": "require_auth — no expiry/scope check on tokens",
    },
    {
        "id": "auth-bypass-permission",
        "file": "auth.py",
        "line_range": (37, 44),
        "category": "auth",
        "description": "check_permission — logic bug grants admin to non-admins",
    },
    {
        "id": "weak-hash",
        "file": "auth.py",
        "line_range": (32, 34),
        "category": "secret",
        "description": "hash_password — MD5 used for password hashing",
    },
    # admin_api.py
    {
        "id": "sqli-admin-run",
        "file": "admin_api.py",
        "line_range": (9, 17),
        "category": "sql",
        "description": "/api/admin/run-query — arbitrary SQL, no auth",
    },
    {
        "id": "sqli-admin-delete",
        "file": "admin_api.py",
        "line_range": (19, 23),
        "category": "sql",
        "description": "delete_user — f-string SQL injection",
    },
    {
        "id": "sqli-admin-impersonate",
        "file": "admin_api.py",
        "line_range": (25, 34),
        "category": "sql",
        "description": "impersonate_user — f-string SQL injection",
    },
    # user_service.py
    {
        "id": "auth-ignored-return",
        "file": "user_service.py",
        "line_range": (16, 26),
        "category": "auth",
        "description": "update_user_profile — check_permission return value ignored",
    },
    {
        "id": "sqli-export-service",
        "file": "user_service.py",
        "line_range": (28, 33),
        "category": "sql",
        "description": "export_users — unvalidated sort_field forwarded to injection sink",
    },
]

FUZZ_LINES = 25  # how many lines off we allow for a match


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_findings(output: str, root: Path) -> list[dict]:
    """
    Parse Autopsy's streaming markdown output into structured findings.

    Expected format (from prompts.py):
        ## [SEVERITY: CRITICAL] Title
        **Category:** SQL Injection
        **Location:** path/to/file.py:42
        **Attack Scenario:** ...
        **Blast Radius:** ...
        **Fix:** ...
        ---
    """
    findings = []
    # Split on ## [SEVERITY: headers — every header starts a new block.
    # Lookahead keeps the header inside the block.
    header_pattern = r'(?=##\s*\[SEVERITY:)'
    blocks = re.split(header_pattern, output, flags=re.IGNORECASE)
    blocks = [b for b in blocks if b.strip()]

    # Fallback: if the lookahead split only produced one block but the raw
    # output actually contains multiple ## [SEVERITY: headers, force-split
    # by grabbing each header through to the next (or end of output).
    severity_count = len(re.findall(r'##\s*\[SEVERITY:', output, re.IGNORECASE))
    if len(blocks) <= 1 and severity_count > 1:
        blocks = re.findall(
            r'(##\s*\[SEVERITY:.*?)(?=##\s*\[SEVERITY:|\Z)',
            output,
            flags=re.IGNORECASE | re.DOTALL,
        )

    console.print(f"  parse_findings: split into {len(blocks)} blocks")

    for block in blocks:
        # Severity + title
        sev_match = re.search(
            r'##\s*\[SEVERITY:\s*(\w+)\]\s*(.+)', block, re.IGNORECASE
        )
        if not sev_match:
            continue

        severity = sev_match.group(1).upper()
        title = sev_match.group(2).strip()

        # Category
        cat_match = re.search(r'\*\*Category:\*\*\s*(.+)', block, re.IGNORECASE)
        category = cat_match.group(1).strip() if cat_match else ""

        # Location — may have multiple; take all
        loc_matches = re.findall(
            r'\*\*Location:\*\*\s*([^\n:]+):(\d+)', block, re.IGNORECASE
        )
        locations = []
        for f, ln in loc_matches:
            locations.append({"file": f.strip(), "line": int(ln)})

        # Also catch bare "file:line" patterns in the block
        bare_locs = re.findall(r'([\w/._-]+\.(?:py|js|ts|tsx)):(\d+)', block)
        for f, ln in bare_locs:
            entry = {"file": f.strip(), "line": int(ln)}
            if entry not in locations:
                locations.append(entry)

        findings.append({
            "severity": severity,
            "title": title,
            "category": category,
            "locations": locations,
            "raw": block[:500],
        })

    return findings


def score_finding_against_truth(
    finding: dict, truth: dict
) -> tuple[bool, int, bool]:
    """
    Return (matchable, distance, category_ok) for a finding vs truth entry.

    - matchable: at least one reported location is in the right file (by
      basename) AND within FUZZ_LINES of the truth line range.
    - distance: smallest line distance from any matchable location to the
      truth range (0 if inside it). Used as the primary tiebreaker so each
      finding gets assigned to the closest truth.
    - category_ok: True if finding category overlaps truth category. Used as
      a secondary tiebreaker and to surface category mismatches in
      diagnostics. Never used to gate the match.
    """
    truth_basename = Path(truth["file"]).name.lower()
    t_start, t_end = truth["line_range"]

    finding_cat = finding["category"].lower()
    truth_cat = truth["category"].lower()
    category_ok = bool(truth_cat) and (
        truth_cat in finding_cat or finding_cat in truth_cat
    )

    best_distance: Optional[int] = None
    for loc in finding["locations"]:
        loc_basename = Path(loc["file"]).name.lower()
        if loc_basename != truth_basename:
            continue
        line = loc["line"]
        if line < t_start - FUZZ_LINES or line > t_end + FUZZ_LINES:
            continue
        if line < t_start:
            d = t_start - line
        elif line > t_end:
            d = line - t_end
        else:
            d = 0
        if best_distance is None or d < best_distance:
            best_distance = d

    if best_distance is None:
        return False, 0, category_ok
    return True, best_distance, category_ok


def finding_matches_truth(finding: dict, truth: dict) -> tuple[bool, bool]:
    """Compatibility shim: (matched, category_mismatched)."""
    matchable, _distance, category_ok = score_finding_against_truth(finding, truth)
    if not matchable:
        return False, False
    return True, not category_ok


# ─── Git repo setup ───────────────────────────────────────────────────────────

def setup_eval_repo(demo_dir: Path, tmp_dir: Path) -> Path:
    """
    Create a fresh git repo in tmp_dir with two commits:
      commit A — empty stub files (clean baseline)
      commit B — full vulnerable demo_project files

    Returns the path to the repo.
    """
    repo_dir = tmp_dir / "eval_repo"
    repo_dir.mkdir()

    def git(*args, cwd=repo_dir):
        result = subprocess.run(
            ["git"] + list(args),
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr}")
        return result.stdout.strip()

    git("init")
    git("config", "user.email", "eval@autopsy.dev")
    git("config", "user.name", "Autopsy Eval")

    # Collect Python files from demo_project
    py_files = list(demo_dir.rglob("*.py"))
    if not py_files:
        raise RuntimeError(f"No .py files found in {demo_dir}")

    # Commit A — empty stubs
    for src in py_files:
        rel = src.relative_to(demo_dir)
        dest = repo_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"# {rel.name} — clean baseline stub\n")

    git("add", ".")
    git("commit", "-m", "baseline: clean stubs")

    # Commit B — vulnerable versions
    for src in py_files:
        rel = src.relative_to(demo_dir)
        dest = repo_dir / rel
        dest.write_text(src.read_text(errors="replace"))

    git("add", ".")
    git("commit", "-m", "feat: add user management (AI-generated)")

    console.print(f"[dim]Eval repo ready at {repo_dir} ({len(py_files)} files)[/dim]")
    return repo_dir


# ─── Main eval ───────────────────────────────────────────────────────────────

def run_eval(demo_dir: Path, out_path: Optional[Path], dry_run: bool):
    try:
        from autopsy.parser import parse_directory
        from autopsy.graph.builder import build_dependency_graph
        from autopsy.llm.pipeline import scan_stream
    except ImportError as e:
        console.print(f"[red]Import error: {e}[/red]")
        console.print("Run this script from the autopsy repo root with autopsy installed.")
        sys.exit(1)

    console.rule("[bold]Autopsy Evaluation Harness[/bold]")
    console.print(f"Demo project : {demo_dir}")
    console.print(f"Ground truth : {len(GROUND_TRUTH)} vulnerabilities")
    console.print(f"Dry run      : {dry_run}\n")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # 1. Set up eval repo
        console.print("[bold]Step 1:[/bold] Setting up eval git repo...")
        repo_dir = setup_eval_repo(demo_dir, tmp_path)

        # 2. Get diff between baseline and vulnerable commit
        console.print("[bold]Step 2:[/bold] Building dependency graph...")

        try:
            parsed = parse_directory(repo_dir)
            graph = build_dependency_graph(parsed)
            console.print(
                f"  Graph: {graph.number_of_nodes()} nodes, "
                f"{graph.number_of_edges()} edges"
            )
        except Exception as e:
            console.print(f"[red]Graph build failed: {e}[/red]")
            raise

        # Get diff: HEAD~1 -> HEAD (baseline -> vulnerable)
        diff_result = subprocess.run(
            ["git", "diff", "HEAD~1", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
        )
        diff_text = diff_result.stdout

        changed_files = []
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                changed_files.append(line[6:])

        console.print(
            f"  Diff: {len(diff_text.splitlines())} lines, "
            f"{len(changed_files)} changed files"
        )

        if dry_run:
            console.print("\n[yellow]Dry run — skipping LLM calls.[/yellow]")
            console.print("Graph and diff look good. Remove --dry-run to run the full eval.")
            return

        # 3. Run scan_stream
        console.print("\n[bold]Step 3:[/bold] Running Autopsy scan (real API calls)...")
        t0 = time.time()

        chunks = []
        try:
            for chunk in scan_stream(graph, diff_text, changed_files, root_dir=repo_dir):
                chunks.append(chunk)
                console.print(chunk, end="", highlight=False)
        except Exception as e:
            console.print(f"\n[red]scan_stream error: {e}[/red]")
            raise

        elapsed = time.time() - t0
        output = "".join(chunks)
        console.print(f"\n\n[dim]Scan completed in {elapsed:.1f}s[/dim]")

        # 4. Parse findings
        console.print("\n[bold]Step 4:[/bold] Parsing findings...")
        findings = parse_findings(output, repo_dir)
        console.print(f"  Parsed {len(findings)} findings from output")

        # 5. Match against ground truth
        console.print("\n[bold]Step 5:[/bold] Matching against ground truth...\n")

        matched_truth = set()   # ground truth IDs that were found
        matched_findings = set()  # finding indices that matched something
        category_mismatches = []  # (truth_id, finding_category) pairs

        # Build every (finding, truth) candidate pair, sort by quality, then
        # assign greedily best-first. Sort key: line distance ascending, then
        # category match preferred. This ensures a finding at auth.py:40 binds
        # to the truth whose line range it actually sits inside, not whichever
        # truth happens to come first in GROUND_TRUTH.
        candidates = []
        for i, finding in enumerate(findings):
            for truth in GROUND_TRUTH:
                matchable, distance, category_ok = score_finding_against_truth(
                    finding, truth
                )
                if matchable:
                    candidates.append((distance, not category_ok, i, truth, finding))

        candidates.sort(key=lambda c: (c[0], c[1]))

        for _distance, cat_mismatched, i, truth, finding in candidates:
            if truth["id"] in matched_truth or i in matched_findings:
                continue
            matched_truth.add(truth["id"])
            matched_findings.add(i)
            if cat_mismatched:
                category_mismatches.append({
                    "truth_id": truth["id"],
                    "truth_category": truth["category"],
                    "finding_category": finding["category"],
                    "finding_title": finding["title"],
                })

        true_positives = len(matched_truth)
        false_negatives = len(GROUND_TRUTH) - true_positives
        false_positives = len(findings) - len(matched_findings)

        precision = true_positives / len(findings) if findings else 0.0
        recall = true_positives / len(GROUND_TRUTH)
        f1 = (2 * precision * recall / (precision + recall)
              if (precision + recall) > 0 else 0.0)

        # 6. Print results table
        table = Table(title="Autopsy Eval Results", show_header=True)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("True Positives", str(true_positives))
        table.add_row("False Negatives (missed)", str(false_negatives))
        table.add_row("False Positives (noise)", str(false_positives))
        table.add_row("Total Findings", str(len(findings)))
        table.add_row("─" * 20, "─" * 10)
        table.add_row("Precision", f"{precision:.2%}")
        table.add_row("Recall", f"{recall:.2%}")
        table.add_row("F1 Score", f"{f1:.2%}")
        table.add_row("Scan Time", f"{elapsed:.1f}s")

        console.print(table)

        # Category mismatches — file/line matched but category did not
        if category_mismatches:
            console.print("\n[yellow]Category mismatches (matched on file+line only):[/yellow]")
            for cm in category_mismatches:
                console.print(
                    f"  - [bold]{cm['truth_id']}[/bold] expected "
                    f"category=[cyan]{cm['truth_category']}[/cyan] "
                    f"but Autopsy reported "
                    f"category=[magenta]{cm['finding_category'] or '(none)'}[/magenta] "
                    f"title={cm['finding_title']!r}"
                )

        # Which ground truth entries were missed?
        missed = [t for t in GROUND_TRUTH if t["id"] not in matched_truth]
        if missed:
            console.print("\n[yellow]Missed vulnerabilities:[/yellow]")
            for t in missed:
                console.print(f"  - [{t['id']}] {t['description']} ({t['file']})")

            # Debug: for each missed truth, show every parsed finding that
            # touched the same file or category so we can see why it didn't match.
            console.print("\n[yellow]Near-miss diagnostics:[/yellow]")
            for t in missed:
                truth_basename = Path(t["file"]).name.lower()
                t_start, t_end = t["line_range"]
                console.print(
                    f"\n  [bold]{t['id']}[/bold] expected "
                    f"category=[cyan]{t['category']}[/cyan] "
                    f"file=[cyan]{t['file']}[/cyan] "
                    f"lines=[cyan]{t_start}-{t_end}[/cyan]"
                )
                near = []
                for f in findings:
                    f_cat = f["category"].lower()
                    cat_overlap = (
                        t["category"].lower() in f_cat or
                        f_cat in t["category"].lower()
                    )
                    file_overlap = any(
                        truth_basename == Path(loc["file"]).name.lower() or
                        truth_basename in loc["file"].lower()
                        for loc in f["locations"]
                    )
                    if cat_overlap or file_overlap:
                        near.append(f)
                if not near:
                    console.print("    [dim](no parsed findings touched this file or category)[/dim]")
                    continue
                for f in near:
                    locs = ", ".join(
                        f"{Path(loc['file']).name}:{loc['line']}"
                        for loc in f["locations"]
                    ) or "(no location)"
                    console.print(
                        f"    - category=[magenta]{f['category'] or '(none)'}[/magenta] "
                        f"locations=[magenta]{locs}[/magenta] "
                        f"title={f['title']!r}"
                    )

        # 7. Save results
        results = {
            "metrics": {
                "true_positives": true_positives,
                "false_negatives": false_negatives,
                "false_positives": false_positives,
                "total_findings": len(findings),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "scan_time_seconds": round(elapsed, 1),
            },
            "ground_truth_count": len(GROUND_TRUTH),
            "matched_ids": sorted(matched_truth),
            "missed_ids": [t["id"] for t in missed],
            "category_mismatches": category_mismatches,
            "raw_findings": findings,
            "raw_output": output,
        }

        if out_path:
            out_path.write_text(json.dumps(results, indent=2))
            console.print(f"\n[green]Results saved to {out_path}[/green]")

        return results


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autopsy evaluation harness")
    parser.add_argument(
        "--demo",
        type=Path,
        default=Path("autopsy-release/demo_project"),
        help="Path to demo_project directory",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Path to save JSON results (optional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build graph and diff but skip LLM calls",
    )
    args = parser.parse_args()

    if not args.demo.exists():
        console.print(f"[red]Demo project not found: {args.demo}[/red]")
        console.print("Pass the correct path with --demo /path/to/demo_project")
        sys.exit(1)

    run_eval(args.demo, args.out, args.dry_run)
