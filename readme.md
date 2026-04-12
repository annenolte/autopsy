# Autopsy — AI Vulnerability Detective

> *Claude Code wrote it. You accepted it. Autopsy finds what you didn't understand — and what it could cost you.*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-red.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)
[![Built at LAH X](https://img.shields.io/badge/Built%20at-Los%20Altos%20Hacks%20X-red.svg)](https://losaltoshacks.com)

Autopsy is a developer security tool that finds vulnerabilities in AI-generated code by reasoning across your entire dependency graph — not just the file where the bug lives. It detects what Claude Code, Copilot, and Cursor wrote, scans it for vulnerabilities, traces root causes across file boundaries, maps the full blast radius of every finding, and catches vulnerability classes that diff-only tools miss entirely — including code activated by deletion.

**Copilot helps when you already know what to ask. Autopsy starts from zero with you.**

---

## The Problem

Every developer using AI coding assistants is shipping code they didn't fully write — and may not fully understand. When something breaks or gets exploited, the root cause is rarely in the file where the error was thrown. It's three files upstream, in a dependency you accepted from an AI suggestion without reading closely.

Traditional security tools scan files in isolation. They also only watch additions — meaning an entire class of vulnerability introduced by deletion is invisible to them. Autopsy builds a graph of your entire codebase, diffs it across commits, and reasons across the full structure. The difference is the difference between finding a symptom and finding the cause.

---

## Features

### Three Modes

**`s` — SCAN THIS** (`Cmd+Shift+S` in VS Code)

Autopsy reads your git diff, identifies which code was likely written by an AI assistant using 7 heuristic signals, and scans it for vulnerabilities. Before scanning additions, it runs a full deletion analysis pass — catching security controls that were removed and code that was silently activated. Every finding includes:
- Severity badge (CRITICAL / HIGH / MEDIUM / LOW)
- Exact file and line number
- Attack scenario in plain English
- Suggested fix
- **Blast radius** — every file that can reach the vulnerable function

**`d` — DEBUG THIS** (`Cmd+Shift+D` in VS Code)

Describe a bug or paste an error. Autopsy traverses the dependency graph using BFS, identifies which nodes are causally connected to the problem, and streams a full analysis including root cause, causal chain, fix suggestion, and blast radius. The root cause is almost never in the file where the error was thrown.

**`o` — ORIENT ME** (`Cmd+Shift+O` in VS Code)

Point Autopsy at any unfamiliar repo. Get a structured map in seconds: architecture overview, module map, data flow, entry points, and complexity hotspots. Uses graph-theoretic properties — in-degree, out-degree, cycle detection — not just text analysis.

**`g` — GRAPH**

View dependency graph statistics and launch the interactive force-directed visualization (in VS Code) showing every node and edge in your codebase, color-coded by type.

---

## How It Works

### The Dependency Graph

Autopsy's core is a **NetworkX directed graph** built by parsing your entire codebase with **Tree-sitter**. Every function, class, and module is a node. Every function call, import, and inheritance relationship is a directed edge.

```
File A (auth/handler.py)
  └── calls → get_user() in db.py
                └── calls → execute_query() in db.py
                              └── ⚠ SQL Injection here
```

This graph is what separates Autopsy from a linter. A linter sees one file at a time. Autopsy sees the whole structure.

### The Full Scan Pipeline

Every scan runs four phases in sequence:

```
Git Diff
    │
    ▼
┌─────────────────────────┐
│  Phase 1                │  Scan raw diff for deleted comment openers
│  Comment Boundary       │  Flag zero-footprint activations
│  Detection              │  (""", /*, =begin, <!--, etc.)
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Phase 2                │  Build graph at pre-commit SHA
│  Pre/Post Graph Diff    │  Build graph at post-commit SHA
│                         │  Diff: activated nodes, deleted nodes,
│                         │  broken edges, security deletions
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Phase 3                │  Score changed code with 7-signal heuristic
│  AI Authorship          │  Score ≥ 0.5 = likely_ai, scanned first
│  Detection              │  Union with activated_nodes from Phase 2
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Phase 4                │  BFS extracts subgraph (max 50 nodes)
│  LLM Pipeline           │  Claude Haiku triages → JSON
│                         │  Claude Sonnet streams deep analysis
│                         │  Blast radius via reverse BFS
└──────────┬──────────────┘
           │
           ▼
    Terminal / VS Code Panel
    (streamed via SSE)
```

### Deletion Analysis

Autopsy detects three categories of deletion-based vulnerabilities that are invisible to diff-only scanners.

**Comment boundary deletion — zero-footprint activation**

Deleting the opening delimiter of a multiline comment activates an entire dormant block of code. The git diff shows only the removed delimiter — one or two characters. The AST sees a completely new set of live functions that never appear as additions, so every diff-only tool misses them entirely.

```
- """
  def execute_raw_query(sql):        ← this function is now live
      db.execute(sql)                ← SQL injection, never reviewed
  """
```

Autopsy detects deleted comment openers across all supported languages:

| Delimiter | Language |
|-----------|----------|
| `"""` / `'''` | Python |
| `/*` | JS / TS / Java / Go / C / C++ |
| `#=` | Julia |
| `--[[` | Lua |
| `=begin` | Ruby |
| `<!--` | HTML / XML |

When a comment boundary deletion is detected, the activated code block is added to scan targets and passed through the full Haiku → Sonnet pipeline as if it were an addition.

```
⚠  ZERO-FOOTPRINT ACTIVATION DETECTED
─────────────────────────────────────────────────────────────
A comment boundary was deleted. Code previously inside this
comment block is now live and was not caught by diff scanning.

File: auth/handler.py
Deleted delimiter: """  (Python multiline string / docstring opener)

Autopsy is scanning the newly activated code for vulnerabilities.
This code does not appear as additions in your git diff.
```

**Security control deletion**

When a function is removed from the codebase whose name contains security-relevant keywords — `validate`, `authenticate`, `sanitize`, `authorize`, `verify`, `guard`, `protect`, `rate_limit`, `csrf`, `xss`, `escape`, `hash`, `encrypt`, `permission`, `require`, `restrict` — Autopsy flags it and reports every caller that is now unprotected.

```
🚨  SECURITY CONTROL DELETED
─────────────────────────────────────────────────────────────
validate_input() was removed. Its callers may now be unprotected.

Called by: api/routes.py, api/admin.py, middleware/session.py
```

**Broken edge detection**

When a function that still exists calls a function that no longer exists, Autopsy reports the dangling dependency — code that calls nothing, silently failing at runtime.

```
⚠  BROKEN DEPENDENCY DETECTED
─────────────────────────────────────────────────────────────
auth/handler.py::authenticate()  →  utils/crypto.py::hash_password()
hash_password() was deleted. authenticate() is now calling nothing.
```

### Pre/Post Commit Graph Diffing

For deletion analysis, Autopsy builds the dependency graph at two points in time and compares them structurally. File contents are read directly from the git object database using GitPython blob reads into a `TemporaryDirectory` — the working directory is never modified. Node IDs are normalized after snapshot construction so the two graphs are directly comparable.

```python
pre_graph  = build_graph_at_commit(repo_path, pre_commit_sha)
post_graph = build_graph_at_commit(repo_path, post_commit_sha)
graph_diff = diff_graphs(pre_graph, post_graph)

# activated_nodes: in post but not pre — newly live code
# deleted_nodes: in pre but not post — removed functions
# broken_edges: caller exists, callee does not
# security_critical_deletions: deleted security-named functions
```

Any node in `activated_nodes` — whether activated by comment removal, file restructuring, or any other mechanism — is added to scan targets and goes through the same Haiku → Sonnet → blast radius pipeline as explicit additions.

### The Blast Radius

After finding a vulnerability, Autopsy reverses the dependency graph and runs a second BFS traversal — this time backward from the vulnerable node to find every caller chain that reaches it.

```python
# Forward graph: A → B → C (A calls B which calls C)
# Reverse graph: C → B → A (who can reach C?)

reversed_graph = graph.reverse()
blast_radius = bfs(reversed_graph, vulnerable_node)
```

This answers the question traditional tools never ask: *"Who can reach this vulnerability?"* Not just "where is it."

```
⚠ CRITICAL — SQL Injection
  Location: db.py:42 in get_user()
  Attack: Unsanitized user input passed directly to execute()

  Blast Radius — 7 files can reach this vulnerability:
  ├── auth/handler.py       → calls get_user() directly
  ├── api/routes.py         → via auth/handler.py
  ├── middleware/session.py → via api/routes.py
  ├── api/admin.py          → calls get_user() directly
  └── ... 3 more

  Any of these entry points exposes the SQL injection.
```

### AI Authorship Detection

Autopsy uses 7 heuristic signals to detect which code was likely written by an AI coding assistant, and prioritizes scanning that code first:

| Signal | Weight | What it detects |
|--------|--------|-----------------|
| Bulk Addition | 0.20 | Large blocks added in a single commit |
| Boilerplate Density | 0.15 | High ratio of template/scaffold patterns |
| Complete Functions | 0.15 | Fully implemented functions with no TODOs |
| Missing Edge Cases | 0.15 | Functions that handle the happy path only |
| Uniform Style | 0.10 | Suspiciously consistent formatting throughout |
| Generated Comments | 0.10 | Docstrings that describe exactly what the code does |
| Commit Message | 0.15 | "Add feature X" with no context or discussion |

A score ≥ 0.5 marks the code as `likely_ai`. Autopsy scans `likely_ai` sections first, then the rest of the diff.

### Vulnerability Categories

Autopsy detects 9 vulnerability categories:

1. **SQL Injection** — unsanitized input in database queries
2. **XSS** — unescaped user content rendered in HTML
3. **Auth Bypass** — logic flaws that skip authentication
4. **Path Traversal** — reading files outside intended directories
5. **SSRF** — server-side requests to attacker-controlled URLs
6. **Command Injection** — OS commands built from user input
7. **Secrets Exposure** — API keys and tokens in code
8. **Race Conditions** — timing flaws that corrupt state or bypass checks
9. **Unvalidated Input** — user data used without sanitization

---

## Architecture

```
autopsy/
├── cli/
│   └── main.py                    # Typer CLI + interactive REPL (readchar)
├── graph/
│   └── builder.py                 # NetworkX graph construction,
│                                  # build_graph_at_commit,
│                                  # diff_graphs, _normalize_graph_paths
├── parser/
│   └── core.py                    # Tree-sitter repo parsing → AST
├── detection/
│   ├── deletions.py               # Comment boundary detection,
│   │                              # zero-footprint activation,
│   │                              # deletion output formatters
│   ├── heuristics.py              # 7-signal AI authorship detector
│   └── vulnerabilities.py        # 9 vulnerability category definitions
├── traversal/
│   └── core.py                    # BFS subgraph extraction + blast radius
├── llm/
│   ├── pipeline.py                # Full scan pipeline (Phases 1–4)
│   ├── triage.py                  # Claude Haiku fast pass (JSON output)
│   └── analysis.py                # Claude Sonnet deep pass (streaming)
├── server/
│   └── main.py                    # FastAPI server (port 7891)
│       ├── POST /api/debug
│       ├── POST /api/scan
│       ├── POST /api/orient
│       ├── POST /api/graph
│       ├── POST /api/graph/visual
│       └── GET  /api/health
└── vscode/
    ├── extension.ts               # VS Code extension entry point
    ├── panel.ts                   # Streaming webview panel
    ├── diagnostics.ts             # Inline red squiggly underlines
    └── graph.ts                   # Force-directed dependency graph
```

### The VS Code Extension

The extension communicates with Autopsy's FastAPI server over localhost:7891. It auto-starts the server on activation and polls `/api/health` until ready.

- **Streaming webview panel** — results stream character by character via Server-Sent Events
- **Inline diagnostics** — vulnerable lines get red squiggly underlines in the editor
- **Interactive graph** — force-directed visualization with draggable nodes, color-coded by type
- **Problems panel** — all findings surfaced as VS Code diagnostics

### The CLI REPL

Type `autopsy` with no arguments to launch the interactive interface:

```
    A U T O P S Y   v0.1.0
    AI Vulnerability Detective
    ─────────────────────────────────
    Repo: ~/projects/my-app

  > d  DEBUG THIS      Trace a bug across the dependency graph
    s  SCAN THIS       Find vulnerabilities in AI-generated code
    o  ORIENT ME       Map this repo's architecture
    g  GRAPH           Show dependency graph stats
    q  Quit
```

Single-keypress navigation. Returns to menu after each command. Exit with `q` or Ctrl+C.

`autopsy serve` starts the FastAPI server for VS Code extension communication.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Code Parsing | Tree-sitter ≥ 0.23 | AST generation for Python, JS, TS, TSX |
| Graph Engine | NetworkX ≥ 3.2 | Dependency graph construction, traversal, diffing |
| Git Integration | GitPython ≥ 3.1.40 | Diffs, commit history, blob reads for graph snapshots |
| LLM Triage | Claude Haiku 4.5 | Fast JSON triage pass (2048 tokens) |
| LLM Analysis | Claude Sonnet 4.5 | Deep streaming analysis (4096 tokens) |
| Code Embeddings | Voyage AI voyage-code-2 | Semantic similarity for subgraph selection |
| API Server | FastAPI ≥ 0.109 + Uvicorn | Local server for VS Code extension |
| CLI | Typer + Rich + readchar | Interactive terminal REPL |
| VS Code Extension | TypeScript + VS Code API | Editor integration |
| Streaming | Server-Sent Events (SSE) | Real-time output to VS Code panel |

---

## Installation

```bash
pip install autopsy
```

Or from source:

```bash
git clone https://github.com/annenolte/autopsy
cd autopsy
pip install -e .
```

Set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY=your_key_here
```

Install the VS Code extension from the marketplace (search "Autopsy") or install the `.vsix` file directly.

---

## Usage

### CLI

```bash
# Launch interactive mode
autopsy

# Run a scan directly
autopsy scan /path/to/repo

# Debug a specific error
autopsy debug /path/to/repo --error "TypeError: cannot read property of undefined"

# Map a repo's architecture
autopsy orient /path/to/repo

# Start the VS Code server
autopsy serve
```

### VS Code

With the extension installed and a repo open:

- `Cmd+Shift+D` — Debug This
- `Cmd+Shift+S` — Scan This
- `Cmd+Shift+O` — Orient Me

Results stream into the Autopsy panel. Vulnerable lines get red squiggly underlines directly in your editor.

---

## Cost

Autopsy is designed to be cheap to run:

| Component | Cost per session |
|-----------|-----------------|
| Claude Haiku (triage) | ~$0.01–0.05 |
| Claude Sonnet (analysis) | ~$0.10–0.40 |
| Voyage AI (embeddings, optional) | ~$0.01 |
| **Total** | **~$0.12–0.46** |

Cost controls: Haiku handles triage, Sonnet only runs on confirmed findings, subgraph capped at 50 nodes, embeddings cached to disk. Graph snapshots for deletion analysis use direct blob reads with no extra API calls.

---

## Why Autopsy vs. Existing Tools

| | Copilot / Cursor | Sentry | Semgrep | **Autopsy** |
|---|---|---|---|---|
| Finds vulnerabilities proactively | ✗ | ✗ | ✓ | ✓ |
| Knows which files to look at | ✗ | ✗ | ✗ | ✓ |
| Traces cross-file root causes | ✗ | ✓ (post-prod) | ✗ | ✓ |
| Detects AI-generated code | ✗ | ✗ | ✗ | ✓ |
| Maps blast radius | ✗ | ✗ | ✗ | ✓ |
| Catches deletion-activated code | ✗ | ✗ | ✗ | ✓ |
| Detects security control deletion | ✗ | ✗ | ✗ | ✓ |
| Detects broken dependencies | ✗ | ✓ (runtime) | ✗ | ✓ |
| Works before you ship | ✓ | ✗ | ✓ | ✓ |
| No pasting required | ✗ | ✓ | ✓ | ✓ |

Sentry catches your house on fire. Autopsy finds the gas leak before anyone lights a match.

---

## Built With

Built solo in 24 hours at **Los Altos Hacks X** — April 11–12, 2026.

By **Anne Nolte** — [GitHub](https://github.com/annenolte)

---
