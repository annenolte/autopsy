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

### SCAN THIS — `s` / `Cmd+Shift+S`

Reads your git diff, identifies which code was likely written by an AI assistant using 7 heuristic signals, and scans it for vulnerabilities. Before scanning additions, it runs a full deletion analysis pass — catching security controls that were removed and code that was silently activated. Every finding includes:
- Severity badge (CRITICAL / HIGH / MEDIUM / LOW)
- Exact file and line number
- Attack scenario in plain English
- Suggested fix
- Blast radius — every file that can reach the vulnerable function

### DEBUG THIS — `d` / `Cmd+Shift+D`

Describe a bug or paste an error. Autopsy traverses the dependency graph using BFS, identifies which nodes are causally connected to the problem, and streams a full analysis including root cause, causal chain, fix suggestion, and blast radius. The root cause is almost never in the file where the error was thrown.

### ORIENT ME — `o` / `Cmd+Shift+O`

Point Autopsy at any unfamiliar repo. Get a structured map in seconds: architecture overview, module map, data flow, entry points, and complexity hotspots. Uses graph-theoretic properties — in-degree, out-degree, cycle detection — not just text analysis.

### GRAPH — `g`

View dependency graph statistics and launch an interactive force-directed visualization showing every node and edge in your codebase. Nodes are color-coded by type (file, function, class), draggable, searchable, and filterable. Available in both the terminal (opens in browser) and as a VS Code webview panel.

### Inline Diagnostics

After a scan, vulnerable lines get red squiggly underlines directly in the editor. Each diagnostic includes the severity, vulnerability title, and attack scenario. All findings appear in the VS Code Problems panel so you can click through them one by one.

### Lightbulb Quick Fixes

Every vulnerability with a suggested fix gets a lightbulb code action in VS Code. Click the lightbulb (or press `Cmd+.`) on an underlined line to:
- **Single-line fixes** — apply the fix directly with one click
- **Multi-line fixes** — open a side-by-side diff preview showing your file before and after the fix, so you can review before applying

### Inline Annotations

Vulnerable lines get inline annotations after the code showing the severity and title at a glance (e.g. `⚠ HIGH: SQL Injection`), visible without hovering or opening any panel.

### Streaming Webview Panel

All analysis results stream character by character into a styled webview panel inside VS Code via Server-Sent Events. The panel renders markdown with syntax-highlighted code blocks, severity badges, and auto-scrolls during streaming. A pulsing "INVESTIGATING" indicator shows when analysis is in progress.

### Auto-Start Server

The VS Code extension automatically starts the Autopsy FastAPI server in a background terminal on activation and polls `/api/health` until it's ready. No manual setup required — open a repo and start scanning.

### Interactive CLI REPL

Type `autopsy` with no arguments to launch the interactive terminal interface with single-keypress navigation using arrow keys:

```
    💀  A U T O P S Y   v0.1.0
    AI Vulnerability Detective
    ─────────────────────────────────
    Repo: ~/projects/my-app

  > d  DEBUG THIS      Trace a bug across the dependency graph
    s  SCAN THIS       Find vulnerabilities in AI-generated code
    o  ORIENT ME       Map this repo's architecture
    g  GRAPH           Show dependency graph stats
    q  Quit
```

Returns to menu after each command. Exit with `q` or Ctrl+C. Falls back to typed input if `readchar` is not installed.

### Two-Model LLM Pipeline

Every analysis runs through two models in sequence:
1. **Claude Haiku** — fast triage pass that identifies which files and functions are relevant, returns structured JSON
2. **Claude Sonnet** — deep streaming analysis that reasons across the full subgraph, produces detailed findings

Haiku keeps costs low by filtering irrelevant code before Sonnet sees it. Sonnet only runs on confirmed areas of interest.

### Dependency Graph Engine

Autopsy's core is a NetworkX directed graph built by parsing your entire codebase with Tree-sitter. Every function, class, and module is a node. Every function call, import, and inheritance relationship is a directed edge. This graph is what enables cross-file reasoning — a linter sees one file at a time, Autopsy sees the whole structure.

### Blast Radius Computation

After finding a vulnerability, Autopsy reverses the dependency graph and runs BFS backward from the vulnerable node to find every caller chain that reaches it. This answers the question traditional tools never ask: *"Who can reach this vulnerability?"* Not just "where is it."

```
💀 Blast Radius — 7 files can reach this vulnerability:
├── auth/handler.py       → calls get_user() directly
├── api/routes.py         → via auth/handler.py
├── middleware/session.py → via api/routes.py
├── api/admin.py          → calls get_user() directly
└── ... 3 more
```

### AI Authorship Detection

7 heuristic signals detect which code was likely written by an AI coding assistant, and that code gets scanned first:

| Signal | Weight | What it detects |
|--------|--------|-----------------|
| Bulk Addition | 0.20 | Large blocks added in a single commit |
| Boilerplate Density | 0.15 | High ratio of template/scaffold patterns |
| Complete Functions | 0.15 | Fully implemented functions with no TODOs |
| Missing Edge Cases | 0.15 | Functions that handle the happy path only |
| Uniform Style | 0.10 | Suspiciously consistent formatting throughout |
| Generated Comments | 0.10 | Docstrings that describe exactly what the code does |
| Commit Message | 0.15 | "Add feature X" with no context or discussion |

A score >= 0.5 marks the code as `likely_ai`. Autopsy scans `likely_ai` sections first, then the rest of the diff.

### Deletion Analysis

Autopsy detects three categories of deletion-based vulnerabilities that are invisible to diff-only scanners.

**Comment boundary deletion — zero-footprint activation**

Deleting the opening delimiter of a multiline comment activates an entire dormant block of code. The git diff shows only the removed delimiter. The AST sees a completely new set of live functions that never appear as additions, so every diff-only tool misses them entirely.

```
- """
  def execute_raw_query(sql):        ← this function is now live
      db.execute(sql)                ← SQL injection, never reviewed
  """
```

Detected across all supported languages:

| Delimiter | Language |
|-----------|----------|
| `"""` / `'''` | Python |
| `/*` | JS / TS / Java / Go / C / C++ |
| `#=` | Julia |
| `--[[` | Lua |
| `=begin` | Ruby |
| `<!--` | HTML / XML |

**Security control deletion**

When a function is removed whose name contains security-relevant keywords — `validate`, `authenticate`, `sanitize`, `authorize`, `verify`, `guard`, `protect`, `rate_limit`, `csrf`, `xss`, `escape`, `hash`, `encrypt`, `permission`, `require`, `restrict` — Autopsy flags it and reports every caller that is now unprotected.

**Broken edge detection**

When a function that still exists calls a function that no longer exists, Autopsy reports the dangling dependency — code that calls nothing, silently failing at runtime.

### Pre/Post Commit Graph Diffing

For deletion analysis, Autopsy builds the dependency graph at two points in time and compares them structurally. File contents are read directly from the git object database using GitPython blob reads into a temporary directory — the working directory is never modified. Node IDs are normalized after snapshot construction so the two graphs are directly comparable.

### Semantic File Ranking (Optional)

When the `voyageai` package is installed, Autopsy uses Voyage AI's `voyage-code-2` model to compute embeddings for each file in the subgraph and ranks them by cosine similarity to the diff. This narrows the context sent to the LLM to the most semantically relevant files. Embeddings are cached to disk in `.autopsy_cache/` so they only need to be computed once per file version.

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

### FastAPI Server

A local API server on port 7891 provides all Autopsy functionality over HTTP for the VS Code extension and any other client:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/debug` | POST | Stream causal reasoning for a target |
| `/api/scan` | POST | Stream vulnerability scan of git diff |
| `/api/orient` | POST | Stream repository orientation map |
| `/api/graph` | POST | Return graph stats and subgraph summary |
| `/api/graph/visual` | POST | Return graph nodes and edges as JSON |
| `/api/health` | GET | Server health check |

The server caches parsed repos by file fingerprint (SHA-256 of paths + mtimes) so repeated requests to the same unchanged repo are instant.

### Demo Project

The repo includes a `demo_project/` directory with intentionally vulnerable Python code (SQL injection, auth bypass, path traversal) that you can scan to see Autopsy in action without pointing it at your own code.

---

## Architecture

```
autopsy/
├── cli/
│   ├── main.py              # Typer CLI commands (scan, debug, orient, graph, serve)
│   ├── interactive.py        # Arrow-key REPL with readchar
│   └── splash.py             # Header renderer
├── parser/
│   ├── core.py               # Tree-sitter file and directory parsing
│   ├── extractors.py         # Language-specific AST extractors (Python, JS, TS)
│   ├── languages.py          # Tree-sitter language initialization
│   └── models.py             # ParsedFile, FunctionDef, ClassDef, ImportDef, CallSite
├── graph/
│   ├── builder.py            # NetworkX graph construction, build_graph_at_commit,
│   │                         # diff_graphs, path normalization
│   ├── subgraph.py           # BFS subgraph extraction, file content loading
│   ├── traversal.py          # Blast radius via reverse BFS
│   └── visualize.py          # Standalone HTML force-directed graph visualization
├── detection/
│   ├── deletions.py          # Comment boundary detection, zero-footprint activation,
│   │                         # security deletion + broken edge formatters
│   └── heuristics.py         # 7-signal AI authorship detector
├── llm/
│   ├── client.py             # Anthropic API client (Haiku non-streaming, Sonnet streaming)
│   ├── pipeline.py           # Full scan/debug/orient pipelines (Phases 1–4)
│   └── prompts.py            # System prompts for triage, debug, scan, orient
├── cache/
│   └── embeddings.py         # Voyage AI embedding cache (disk-backed JSON)
├── server/
│   └── app.py                # FastAPI server with SSE streaming and repo caching
└── utils/
extension/
├── src/
│   ├── extension.ts          # VS Code extension entry point, code action provider
│   ├── panel.ts              # Streaming markdown webview panel
│   ├── diagnostics.ts        # Inline diagnostics, fix store, gutter annotations
│   ├── graphPanel.ts         # Force-directed graph webview for VS Code
│   └── client.ts             # HTTP/SSE client for the FastAPI backend
├── media/
│   └── mascot.svg            # Autopsy logo
└── package.json              # Extension manifest, commands, keybindings, settings
tests/
├── test_parser.py            # Tree-sitter parsing tests
├── test_graph.py             # Dependency graph construction tests
├── test_heuristics.py        # AI authorship detection tests
├── test_deletions.py         # Deletion analysis tests
├── test_api.py               # FastAPI endpoint tests
└── conftest.py               # Shared test fixtures
demo_project/                  # Intentionally vulnerable code for demo scans
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Code Parsing | Tree-sitter >= 0.23 | AST generation for Python, JS, TS, TSX |
| Graph Engine | NetworkX >= 3.2 | Dependency graph construction, traversal, diffing |
| Git Integration | GitPython >= 3.1.40 | Diffs, commit history, blob reads for graph snapshots |
| LLM Triage | Claude Haiku 4.5 | Fast JSON triage pass (2048 tokens) |
| LLM Analysis | Claude Sonnet 4.5 | Deep streaming analysis (4096 tokens) |
| Code Embeddings | Voyage AI voyage-code-2 | Semantic similarity for subgraph selection (optional) |
| API Server | FastAPI >= 0.109 + Uvicorn | Local server for VS Code extension |
| CLI | Typer + Rich + readchar | Interactive terminal REPL |
| VS Code Extension | TypeScript + VS Code API | Editor integration, diagnostics, code actions |
| Streaming | Server-Sent Events (SSE) | Real-time output to VS Code panel and CLI |

---

## Installation

From source:

```bash
git clone https://github.com/annenolte/autopsy
cd autopsy
pip install -e .
```

Set your Anthropic API key (pick one method):

```bash
# Option 1: Environment variable
export ANTHROPIC_API_KEY=your_key_here

# Option 2: .env file in the repo root
cp .env.example .env
# Then edit .env and paste your key
```

For the VS Code extension, `cd extension && npm install && npm run compile`, then open the `extension/` folder in VS Code and press F5 to launch the Extension Development Host.

Optional — for semantic file ranking:
```bash
pip install "autopsy[embeddings]"
export VOYAGE_API_KEY=your_voyage_key_here
```

---

## Usage

### CLI

```bash
# Launch interactive mode
autopsy

# Run a scan directly
autopsy scan /path/to/repo

# Scan uncommitted changes
autopsy scan /path/to/repo --uncommitted

# Debug a specific error
autopsy debug /path/to/repo --target app.py --query "TypeError: cannot read property of undefined"

# Map a repo's architecture
autopsy orient /path/to/repo

# Show dependency graph stats
autopsy graph /path/to/repo

# Open interactive graph in browser
autopsy graph /path/to/repo --view

# Start the VS Code server
autopsy serve
```

### VS Code

With the extension installed and a repo open:

- `Cmd+Shift+D` — Debug This (prompts for error description, streams causal analysis)
- `Cmd+Shift+S` — Scan This (choose uncommitted or last commit, streams vulnerability scan)
- `Cmd+Shift+O` — Orient Me (streams structured repo map)
- `Autopsy: Show Dependency Graph` — opens interactive force-directed graph in a webview panel

After a scan:
- Red squiggly underlines appear on vulnerable lines
- Inline annotations show severity and title after each flagged line
- Click the lightbulb on any flagged line to preview or apply the suggested fix
- Check the Problems panel for a full list of findings

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
| Finds vulnerabilities proactively | - | - | Yes | Yes |
| Knows which files to look at | - | - | - | Yes |
| Traces cross-file root causes | - | Yes (post-prod) | - | Yes |
| Detects AI-generated code | - | - | - | Yes |
| Maps blast radius | - | - | - | Yes |
| Catches deletion-activated code | - | - | - | Yes |
| Detects security control deletion | - | - | - | Yes |
| Detects broken dependencies | - | Yes (runtime) | - | Yes |
| In-editor fix suggestions | - | - | - | Yes |
| Works before you ship | Yes | - | Yes | Yes |
| No pasting required | - | Yes | Yes | Yes |

Sentry catches your house on fire. Autopsy finds the gas leak before anyone lights a match.

---

## Built With

Built solo in 24 hours at **Los Altos Hacks X** — April 11-12, 2026.

By **Anne Nolte** — [GitHub](https://github.com/annenolte)

---
