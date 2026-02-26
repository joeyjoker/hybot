# HyBot

An interactive AI coding assistant in your terminal, powered by the [agno](https://github.com/agno-agi/agno) framework.

[中文文档 (Chinese)](./README.zh-CN.md)

---

## Features

- **Multi-provider support** — OpenAI Chat Completions, OpenAI Responses API, Anthropic Claude, Google Gemini
- **Built-in tools** — File read/write, shell commands (CodingTools), Python execution (PythonTools)
- **Dangerous operation confirmation** — Intercepts `rm -rf`, `sudo`, `git push --force`, etc. with three configurable modes
- **Persistent memory** — Agent saves and recalls memories across sessions (preferences, lessons learned, etc.)
- **Project awareness** — Auto-detects language, framework, package manager, and directory structure on startup
- **Git tools** — Agent can run git status, diff, log, add, commit, branch, checkout, stash, and show
- **Web tools** — Optional DuckDuckGo search and website content fetching
- **MCP integration** — Connect to any [Model Context Protocol](https://modelcontextprotocol.io/) server via stdio or HTTP
- **Skills system** — Modular skill packages with full lifecycle management (install / remove / catalog)
- **Sub-agents** — Define task-specific sub-agents in YAML; the main agent delegates via tool calls
- **Non-interactive mode** — `hybot --run "task"` for single-shot execution with optional JSON output
- **Session persistence** — SQLite-backed history with resume support
- **Layered config** — Global (`~/.hybot/config.yaml`) + workspace-local (`.hybot/config.yaml`) deep merge
- **AGENT.md** — Project-specific agent instructions loaded automatically at startup
- **Workspace trust** — Explicit user approval before running in a new directory

---

## Quick Start

### Install

```bash
# From source
git clone <repo-url> && cd hybot
pip install -e .

# With web search support
pip install -e ".[web]"

# Provider extras
pip install anthropic        # For Anthropic Claude
pip install google-genai     # For Google Gemini
```

### Run

```bash
export OPENAI_API_KEY=sk-xxx

# Interactive mode
hybot

# Resume a previous session
hybot --session <session-id>

# Non-interactive mode
hybot --run "list all Python files under src/"
hybot --run "analyze project structure" --output json
hybot --run "run tests" --project /path/to/project
```

On first run in a directory, HyBot asks for workspace trust approval and initializes a `.hybot/` directory.

---

## CLI Arguments

| Argument | Description |
|---|---|
| `-c`, `--config PATH` | Config file path (default `~/.hybot/config.yaml`) |
| `-s`, `--session ID` | Resume a specific session |
| `-r`, `--run TEXT` | Execute a single task and exit |
| `-p`, `--project DIR` | Working directory (default: cwd) |
| `--output {text,json}` | Output format (default: `text`) |
| `--no-stream` | Disable streaming output |
| `--debug` | Enable debug mode |

---

## Configuration

Two-level config system — workspace-local deep-merges on top of global. Only override what you need.

| File | Purpose |
|---|---|
| `~/.hybot/config.yaml` | Global defaults |
| `<workspace>/.hybot/config.yaml` | Per-project overrides |

### Full Reference

```yaml
model:
  provider: "openai"            # "openai" | "openai_responses" | "anthropic" | "gemini"
  id: "gpt-4o"
  base_url: null                # Custom API endpoint (openai / openai_responses only)
  api_key: null                 # Falls back to env vars (OPENAI_API_KEY, etc.)
  reasoning_effort: null        # "minimal" | "low" | "medium" | "high"
  reasoning_summary: null       # "auto" | "concise" | "detailed" (openai_responses only)

agent:
  name: "HyBot"
  description: "AI coding assistant"
  instructions:
    - "You are a powerful AI coding assistant."
  markdown: true
  stream: true
  reasoning: false
  show_reasoning: true
  add_history_to_context: true
  num_history_runs: 10
  add_datetime_to_context: true

tools:
  coding:
    enabled: true
    base_dir: "."               # Auto-set to workspace root
    all: true
  python:
    enabled: true
  git:
    enabled: true               # Git tools (status, diff, log, commit, etc.)
  web:
    enabled: false              # Disabled by default to avoid unintended network access
    enable_search: true         # DuckDuckGo search
    enable_fetch: true          # Website content fetching

memory:
  enabled: true
  path: "~/.hybot/memory"

approval:
  mode: "dangerous"             # "always" | "dangerous" | "never"

project:
  scan_on_startup: true
  cache_scan: true

storage:
  type: "sqlite"
  db_file: "~/.hybot/sessions.db"  # Auto-overridden to <workspace>/.hybot/sessions.db

skills:
  path: "~/.hybot/skills"

mcp_servers: []
# - name: "filesystem"
#   command: "npx -y @modelcontextprotocol/server-filesystem /tmp"
# - name: "my-server"
#   url: "http://localhost:8080"
#   transport: "streamable-http"
```

### Provider Examples

```yaml
# OpenAI Chat Completions (default)
model:
  id: gpt-4o

# OpenAI Responses API with reasoning
model:
  provider: openai_responses
  id: o3
  reasoning_effort: high
  reasoning_summary: detailed

# Anthropic Claude
model:
  provider: anthropic
  id: claude-sonnet-4-5-20250929

# Google Gemini
model:
  provider: gemini
  id: gemini-2.0-flash-001

# OpenAI-compatible endpoint
model:
  id: deepseek-chat
  base_url: https://api.deepseek.com/v1
```

### Approval Modes

| Mode | Behavior |
|---|---|
| `dangerous` (default) | Prompts confirmation only for dangerous shell commands (`rm -rf`, `sudo`, `chmod`, `dd`, `git push --force`, etc.) |
| `always` | Prompts confirmation for every shell command and file write |
| `never` | No confirmation prompts |

---

## Slash Commands

| Command | Description |
|---|---|
| `/help` or `/` | Show all available commands |
| `/resume` | List recent sessions and restore one |
| `/init` | Re-initialize the current workspace |
| `/skills` | List loaded skills |
| `/config` | Show current merged config |
| `/reasoning` | Toggle reasoning mode |
| `/thinking` | Toggle reasoning display |
| `/memory` | Show persistent memory entries |
| `/project` | Show detected project info |
| `/project rescan` | Force re-scan project structure |
| `/skill list` | List all skills (global + project) |
| `/skill install <name>` | Install skill from global library to project |
| `/skill remove <name>` | Remove skill from project |
| `/skill catalog <name>` | Publish project skill to global library |
| `/mcp list` | List configured MCP servers |
| `/mcp add <name>` | Add MCP server from registry to project config |
| `/mcp remove <name>` | Remove MCP server from project config |
| `/exit` | Exit HyBot |

You can also type `exit`, `quit`, `bye`, or press `Ctrl+C` to leave.

---

## Persistent Memory

The Agent can save, query, and delete memories that persist across sessions. Memories are stored as markdown files under `~/.hybot/memory/`.

**Agent tools:**
- `save_memory(category, content)` — Save to a named category (e.g. `preferences`, `lessons_learned`)
- `list_memories()` — List all memory categories with previews
- `delete_memory(category)` — Delete a category

**Example:**

```
> User: Remember that I prefer TypeScript over JavaScript
# Agent calls save_memory("preferences", "User prefers TypeScript over JavaScript")

> User: /memory
# Displays a table of all saved memory categories and previews
```

---

## Project Awareness

On startup, HyBot scans the workspace to detect:

- **Languages** — Python, JavaScript/TypeScript, Rust, Go, Java, C/C++, C#, Ruby, PHP, Dart, Elixir
- **Package managers** — pip, poetry, uv, npm, yarn, pnpm, bun, cargo, go modules, maven, gradle, etc.
- **Frameworks** — Django, Flask, Next.js, Nuxt, Angular, Vite, pytest, etc.
- **Directory structure** — `src/`, `tests/`, `docs/`, `scripts/`, etc.
- **Entry files** — `main.py`, `app.py`, `index.ts`, `index.js`, `main.go`, `main.rs`
- **Git info** — Remote URL, current branch

Results are injected into the Agent's context and cached to `.hybot/project_info.md`. Use `/project rescan` to refresh.

---

## Git Tools

Enabled by default (`tools.git.enabled: true`). The Agent can call:

| Tool | Description |
|---|---|
| `git_status()` | Working tree status |
| `git_diff(cached, file_path)` | View diff (staged or unstaged) |
| `git_log(max_entries, oneline)` | Commit history |
| `git_add(paths)` | Stage files |
| `git_commit(message)` | Create a commit |
| `git_branch(create, delete)` | List, create, or delete branches |
| `git_checkout(ref, create)` | Switch branches or create new ones |
| `git_stash(action, message)` | Push, pop, list, or drop stashes |
| `git_show(ref)` | Show commit details |

---

## Web Tools

Disabled by default to avoid unintended network access. Enable in config:

```yaml
tools:
  web:
    enabled: true
```

Requires the `web` extra:

```bash
pip install -e ".[web]"
```

Provides DuckDuckGo search (`enable_search`) and website content fetching (`enable_fetch`).

---

## Sub-agents

Define sub-agents as YAML files in `.hybot/agents/`. The main Agent delegates tasks to them via tool calls.

**Example:** `.hybot/agents/code_reviewer.yaml`

```yaml
name: code_reviewer
description: Reviews code quality and style
model:
  provider: openai
  id: gpt-4o-mini
instructions:
  - "You are a strict code reviewer."
  - "Check for style issues, potential bugs, and performance problems."
tools:
  - coding
```

This creates an `invoke_code_reviewer(task)` tool for the main Agent. Sub-agents are lazily loaded on first invocation.

**Available tool names for sub-agents:**
- `coding` — File operations and shell commands
- `python` — Python code execution
- `git` — Git operations

---

## Non-interactive Mode

Use `--run` to execute a single task and exit:

```bash
hybot --run "list all Python files under src/"
hybot --run "analyze project structure" --output json
hybot --run "run tests" --project /path/to/project
hybot --run "explain main.py" --no-stream
```

JSON output follows the `RunSummary` schema:

```json
{
  "status": "success",
  "summary": "Task completion summary",
  "files_modified": ["src/main.py"],
  "files_created": [],
  "commands_run": ["python -m pytest"],
  "errors": []
}
```

The `--run` mode automatically trusts the target workspace (no interactive confirmation).

---

## AGENT.md

Write project-specific instructions in `AGENT.md`. HyBot loads from three locations (all combined):

1. `~/.hybot/AGENT.md` — Global
2. `<workspace>/AGENT.md` — Project root
3. `<workspace>/.hybot/AGENT.md` — Workspace local

---

## MCP Servers

```yaml
mcp_servers:
  # stdio transport — spawns a subprocess
  - name: "filesystem"
    command: "npx -y @modelcontextprotocol/server-filesystem /tmp"

  # HTTP transport — connects to a running server
  - name: "my-server"
    url: "http://localhost:8080"
    transport: "streamable-http"
    env:
      API_KEY: "xxx"
```

**MCP Registry:** Create `~/.hybot/mcp_registry.yaml` to define reusable templates, then use `/mcp add <name>` to add them to any project.

```yaml
# ~/.hybot/mcp_registry.yaml
servers:
  filesystem:
    command: "npx -y @modelcontextprotocol/server-filesystem /tmp"
  brave-search:
    command: "npx -y @anthropic/mcp-server-brave-search"
    env:
      BRAVE_API_KEY: "xxx"
```

---

## Skills

Place skill packages in the skills directory (`~/.hybot/skills/` by default). HyBot discovers and loads them at startup.

**Lifecycle commands:**

| Command | Description |
|---|---|
| `/skill list` | List skills in global library and project |
| `/skill install <name>` | Copy from global library to project |
| `/skill remove <name>` | Remove from project |
| `/skill catalog <name>` | Publish project skill to global library |

---

## Project Structure

```
src/hybot/
├── __init__.py
├── __main__.py          # CLI entry point with --run support
├── agent.py             # Agent builder, interactive loop & non-interactive mode
├── commands.py          # Slash command registry & dispatch
├── config.py            # Pydantic config models & layered loading
├── memory.py            # Persistent memory (MemoryStore + MemoryTools)
├── project_scanner.py   # Project structure detection & caching
├── schemas.py           # Structured output models (RunSummary)
├── subagent.py          # Sub-agent YAML loading & dynamic tool registration
├── lifecycle.py         # Skill & MCP lifecycle management
└── tools/
    ├── __init__.py
    ├── guarded_coding.py  # CodingTools with danger confirmation
    └── git_tools.py       # Git CLI wrapper toolkit
```

---

## License

MIT
