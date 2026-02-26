# HyBot

一个运行在终端的交互式 AI 编码助手，基于 [agno](https://github.com/agno-agi/agno) 框架构建。

[English](./README.md)

---

## Features / 功能特性

- **Multi-provider support / 多模型 Provider 支持** — OpenAI Chat Completions, OpenAI Responses API, Anthropic Claude, Google Gemini
- **Built-in tools / 内置工具** — File read/write, shell commands (CodingTools), Python execution (PythonTools)
- **Dangerous operation confirmation / 危险操作确认** — Shell 命令 `rm -rf`、`sudo` 等自动拦截，支持 always / dangerous / never 三种模式
- **Persistent memory / 持久记忆** — Agent 可跨会话保存和读取记忆（偏好、经验教训等），存储于 `~/.hybot/memory/`
- **Project awareness / 项目感知** — 自动识别项目语言、框架、包管理器、目录结构，注入 Agent 上下文
- **Git tools / Git 工具** — Agent 可直接执行 git status / diff / log / add / commit / branch / checkout / stash / show
- **Web tools / Web 工具** — 可选启用 DuckDuckGo 搜索和网页读取（需安装 `web` extra）
- **MCP integration / MCP 集成** — Connect to any [Model Context Protocol](https://modelcontextprotocol.io/) server via stdio or HTTP
- **Skills system / 技能系统** — Modular, reusable skill packages with lifecycle management (install / remove / catalog)
- **Sub-agents / 子 Agent** — 通过 YAML 定义子 Agent，主 Agent 可委派任务
- **Non-interactive mode / 非交互模式** — `hybot --run "任务"` 单次执行，支持 JSON 结构化输出
- **Session persistence / 会话持久化** — SQLite-backed session history with resume support
- **Layered config / 分层配置** — Global (`~/.hybot/config.yaml`) + workspace-local (`.hybot/config.yaml`) deep merge
- **AGENT.md** — Project-specific agent instructions, loaded automatically at startup / 项目级 Agent 指令，启动时自动加载
- **Workspace trust / 工作区信任** — Explicit approval before running in a new directory / 在新目录运行前需显式授权

---

## Quick Start / 快速开始

### Install / 安装

```bash
# From source / 从源码安装
git clone <repo-url> && cd hybot
pip install -e .

# With web search support / 启用 Web 搜索
pip install -e ".[web]"

# For Anthropic Claude support / 如需使用 Claude
pip install anthropic
# or: pip install agno[anthropic]

# For Google Gemini support / 如需使用 Gemini
pip install google-genai
# or: pip install agno[google]
```

### Run / 运行

```bash
# Set your API key / 设置 API 密钥
export OPENAI_API_KEY=sk-xxx

# Launch interactive mode / 启动交互模式
hybot

# Resume a previous session / 恢复历史会话
hybot --session <session-id>

# Non-interactive: run a single task / 非交互：执行单个任务
hybot --run "列出 src/ 下所有 Python 文件"

# JSON output / JSON 结构化输出
hybot --run "分析项目结构" --output json

# Specify working directory / 指定工作目录
hybot --run "运行测试" --project /path/to/project

# Use a custom config file / 指定配置文件
hybot --config /path/to/config.yaml
```

On first run in a directory, HyBot will ask for workspace trust approval and initialize a `.hybot/` directory.

首次在某目录运行时，HyBot 会请求工作区信任授权并初始化 `.hybot/` 目录。

---

## CLI Arguments / 命令行参数

| Argument / 参数 | Description / 说明 |
|---|---|
| `-c`, `--config PATH` | Config file path / 配置文件路径（默认 `~/.hybot/config.yaml`） |
| `-s`, `--session ID` | Resume a session / 恢复指定会话 |
| `-r`, `--run TEXT` | Non-interactive: execute a task and exit / 非交互执行任务后退出 |
| `-p`, `--project DIR` | Working directory / 指定工作目录（默认当前目录） |
| `--output {text,json}` | Output format / 输出格式（默认 `text`） |
| `--no-stream` | Disable streaming / 禁用流式输出 |
| `--debug` | Enable debug mode / 启用调试模式 |

---

## Configuration / 配置

HyBot uses a two-level config system. The workspace-local config deep-merges on top of the global config — only override what you need.

HyBot 采用两级配置系统。工作区本地配置会深度合并覆盖全局配置，只需填写需要覆盖的字段。

| File / 文件 | Purpose / 用途 |
|---|---|
| `~/.hybot/config.yaml` | Global defaults / 全局默认配置 |
| `<workspace>/.hybot/config.yaml` | Per-project overrides / 项目级覆盖配置 |

### Full Config Reference / 完整配置参考

```yaml
model:
  provider: "openai"            # "openai" | "openai_responses" | "anthropic" | "gemini"
  id: "gpt-4o"                  # Model ID
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
    enable_search: true         # DuckDuckGo web search
    enable_fetch: true          # Website content fetching

memory:
  enabled: true                 # Persistent memory system
  path: "~/.hybot/memory"       # Memory storage directory

approval:
  mode: "dangerous"             # "always" | "dangerous" | "never"

project:
  scan_on_startup: true         # Auto-detect project structure on startup
  cache_scan: true              # Cache scan results to .hybot/project_info.md

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

### Provider Examples / Provider 配置示例

```yaml
# OpenAI Chat Completions (default / 默认)
model:
  id: gpt-4o

# OpenAI Responses API with reasoning / 使用 Responses API + 推理模型
model:
  provider: openai_responses
  id: o3
  reasoning_effort: high
  reasoning_summary: detailed

# Anthropic Claude
model:
  provider: anthropic
  id: claude-sonnet-4-5-20250929
  api_key: sk-ant-xxx

# Google Gemini
model:
  provider: gemini
  id: gemini-2.0-flash-001
  api_key: AIzaSyxxx

# OpenAI-compatible endpoint / 兼容 OpenAI 的第三方端点
model:
  id: deepseek-chat
  base_url: https://api.deepseek.com/v1
  api_key: sk-xxx
```

### Approval Modes / 操作确认模式

| Mode | Behavior / 行为 |
|---|---|
| `dangerous` (default) | 仅对危险 shell 命令弹出确认（`rm -rf`、`sudo`、`chmod`、`dd`、`git push --force` 等） |
| `always` | 所有 shell 命令和文件写入都弹出确认 |
| `never` | 不弹出任何确认 |

---

## Slash Commands / 斜杠命令

Type these in the interactive prompt:

在交互式提示符中输入以下命令：

| Command / 命令 | Description / 说明 |
|---|---|
| `/help` or `/` | Show all available commands / 显示所有可用命令 |
| `/resume` | List recent sessions and restore one / 列出最近会话并选择恢复 |
| `/init` | Re-initialize the current workspace / 重新初始化当前工作区 |
| `/skills` | List loaded skills / 列出已加载的技能 |
| `/config` | Show current merged config / 显示当前合并后的配置 |
| `/reasoning` | Toggle reasoning mode / 开关推理模式 |
| `/thinking` | Toggle reasoning display / 开关思考过程显示 |
| `/memory` | Show persistent memory entries / 查看持久记忆列表 |
| `/project` | Show project info / 查看项目信息 |
| `/project rescan` | Force re-scan project structure / 强制重新扫描项目结构 |
| `/skill list` | List all skills (global + project) / 列出所有技能 |
| `/skill install <name>` | Install skill from global library / 从全局库安装技能到项目 |
| `/skill remove <name>` | Remove skill from project / 从项目移除技能 |
| `/skill catalog <name>` | Publish project skill to global library / 将项目技能上报到全局库 |
| `/mcp list` | List configured MCP servers / 列出已配置的 MCP 服务 |
| `/mcp add <name>` | Add MCP server from registry / 从注册表添加 MCP 服务到项目 |
| `/mcp remove <name>` | Remove MCP server from project / 从项目移除 MCP 服务 |
| `/exit` | Exit HyBot / 退出 |

You can also type `exit`, `quit`, or `bye` to leave, or press `Ctrl+C`.

也可以输入 `exit`、`quit`、`bye` 或按 `Ctrl+C` 退出。

---

## Persistent Memory / 持久记忆

HyBot's Agent can save, query, and delete memories that persist across sessions. Memories are stored as markdown files under `~/.hybot/memory/`.

Agent 可跨会话保存、查询和删除记忆。记忆以 Markdown 文件形式存储在 `~/.hybot/memory/` 目录下。

**Agent tools / Agent 工具：**
- `save_memory(category, content)` — Save a memory (e.g. preferences, lessons_learned)
- `list_memories()` — List all memory categories
- `delete_memory(category)` — Delete a memory category

**Example / 示例：**

```
> User: 记住我偏好用中文回复，代码注释也用中文
# Agent 会调用 save_memory("preferences", "用户偏好中文回复和中文代码注释")

> User: /memory
# 显示所有已保存的记忆分类和内容预览
```

---

## Project Awareness / 项目感知

On startup, HyBot scans the workspace to detect:

启动时，HyBot 自动扫描工作区以识别：

- **Languages / 语言** — Python, JavaScript/TypeScript, Rust, Go, Java, etc.
- **Package managers / 包管理器** — pip, poetry, npm, yarn, cargo, etc.
- **Frameworks / 框架** — Django, Flask, Next.js, Nuxt, Angular, etc.
- **Directory structure / 目录结构** — src/, tests/, docs/, etc.
- **Entry files / 入口文件** — main.py, app.py, index.ts, etc.
- **Git info / Git 信息** — remote URL, current branch

Results are injected into the Agent's context and cached to `.hybot/project_info.md`. Use `/project rescan` to refresh.

扫描结果会注入 Agent 上下文并缓存到 `.hybot/project_info.md`。使用 `/project rescan` 可强制刷新。

---

## Git Tools / Git 工具

When `tools.git.enabled: true` (default), the Agent has access to:

当 `tools.git.enabled: true`（默认开启）时，Agent 可使用以下工具：

| Tool / 工具 | Description / 说明 |
|---|---|
| `git_status()` | Working tree status / 工作树状态 |
| `git_diff(cached, file_path)` | View diff / 查看差异 |
| `git_log(max_entries, oneline)` | Commit history / 提交历史 |
| `git_add(paths)` | Stage files / 暂存文件 |
| `git_commit(message)` | Create commit / 创建提交 |
| `git_branch(create, delete)` | Branch management / 分支管理 |
| `git_checkout(ref, create)` | Switch branch / 切换分支 |
| `git_stash(action, message)` | Stash management / 储藏管理 |
| `git_show(ref)` | Show commit details / 查看提交详情 |

---

## Web Tools / Web 工具

Disabled by default. Enable in config:

默认关闭。在配置中启用：

```yaml
tools:
  web:
    enabled: true
    enable_search: true   # DuckDuckGo search / DuckDuckGo 搜索
    enable_fetch: true    # Website content fetching / 网页内容抓取
```

Requires the `web` extra:

需要安装 `web` 可选依赖：

```bash
pip install -e ".[web]"
```

---

## Sub-agents / 子 Agent

Define sub-agents as YAML files in `.hybot/agents/`. The main Agent can delegate tasks to them via tool calls.

在 `.hybot/agents/` 中以 YAML 文件定义子 Agent。主 Agent 可通过工具调用将任务委派给它们。

**Example / 示例：** `.hybot/agents/code_reviewer.yaml`

```yaml
name: code_reviewer
description: 审查代码质量和风格
model:
  provider: openai
  id: gpt-4o-mini
instructions:
  - "你是一个严格的代码审查员。"
  - "检查代码风格、潜在 bug 和性能问题。"
tools:
  - coding
```

The main Agent will have an `invoke_code_reviewer(task)` tool available. Sub-agents are lazily loaded on first invocation.

主 Agent 将获得 `invoke_code_reviewer(task)` 工具。子 Agent 在首次调用时才构建。

**Available tool names for sub-agents / 子 Agent 可用工具名：**
- `coding` — CodingTools (file operations, shell commands)
- `python` — PythonTools (Python code execution)
- `git` — GitTools (git operations)

---

## AGENT.md

Write project-specific instructions in `AGENT.md`. HyBot loads them from three locations (all combined if present):

在 `AGENT.md` 中编写项目专属指令。HyBot 从以下三个位置加载（如存在则全部合并）：

1. `~/.hybot/AGENT.md` — Global / 全局
2. `<workspace>/AGENT.md` — Project root / 项目根目录
3. `<workspace>/.hybot/AGENT.md` — Workspace local / 工作区本地

---

## MCP Servers / MCP 服务器

Add MCP servers to extend HyBot's capabilities:

添加 MCP 服务器以扩展 HyBot 的能力：

```yaml
mcp_servers:
  # stdio transport — spawns a subprocess / 标准 IO 传输 — 启动子进程
  - name: "filesystem"
    command: "npx -y @modelcontextprotocol/server-filesystem /tmp"

  # HTTP transport — connects to a running server / HTTP 传输 — 连接运行中的服务器
  - name: "my-server"
    url: "http://localhost:8080"
    transport: "streamable-http"
    env:
      API_KEY: "xxx"
```

**MCP Registry / MCP 注册表：** Create `~/.hybot/mcp_registry.yaml` to define reusable MCP server templates. Then use `/mcp add <name>` to quickly add them to a project.

创建 `~/.hybot/mcp_registry.yaml` 定义可复用的 MCP 服务模板，然后用 `/mcp add <name>` 快速添加到项目。

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

## Skills / 技能

Place skill packages in the skills directory (`~/.hybot/skills/` by default). HyBot discovers and loads them automatically at startup.

将技能包放入技能目录（默认为 `~/.hybot/skills/`），HyBot 在启动时自动发现并加载。

**Lifecycle management / 生命周期管理：**

| Command / 命令 | Description / 说明 |
|---|---|
| `/skill list` | List skills in global library and project / 列出全局库和项目中的技能 |
| `/skill install <name>` | Copy skill from global library to project / 从全局库安装到项目 |
| `/skill remove <name>` | Remove skill from project / 从项目移除 |
| `/skill catalog <name>` | Publish project skill to global library / 将项目技能上报到全局库 |

---

## Non-interactive Mode / 非交互模式

Use `--run` to execute a single task and exit:

使用 `--run` 执行单个任务后退出：

```bash
# Text output (default) / 文本输出（默认）
hybot --run "列出 src/ 下所有 Python 文件"

# JSON structured output / JSON 结构化输出
hybot --run "分析项目结构" --output json

# Specify project directory / 指定项目目录
hybot --run "运行测试" --project /path/to/project

# Disable streaming / 禁用流式输出
hybot --run "解释 main.py" --no-stream
```

JSON output follows the `RunSummary` schema:

JSON 输出遵循 `RunSummary` 结构：

```json
{
  "status": "success",
  "summary": "任务完成摘要",
  "files_modified": ["src/main.py"],
  "files_created": [],
  "commands_run": ["python -m pytest"],
  "errors": []
}
```

The `--run` mode automatically trusts the specified workspace (no interactive confirmation prompt).

`--run` 模式自动信任指定的工作区（不弹出交互式确认）。

---

## Project Structure / 项目结构

```
src/hybot/
├── __init__.py
├── __main__.py          # CLI entry point with --run support / CLI 入口，支持 --run
├── agent.py             # Agent builder, interactive loop & non-interactive mode / Agent 构建与运行
├── commands.py          # Slash command registry / 斜杠命令注册
├── config.py            # Config models & loading / 配置模型与加载
├── memory.py            # Persistent memory (MemoryStore + MemoryTools) / 持久记忆
├── project_scanner.py   # Project structure detection / 项目结构探测
├── schemas.py           # Structured output models (RunSummary) / 结构化输出
├── subagent.py          # Sub-agent loading & tools / 子 Agent 加载
├── lifecycle.py         # Skill & MCP lifecycle management / 技能与 MCP 生命周期
└── tools/
    ├── __init__.py
    ├── guarded_coding.py  # CodingTools with danger confirmation / 带确认的 CodingTools
    └── git_tools.py       # Git CLI wrapper tools / Git 工具
```

---

## License / 许可证

MIT
