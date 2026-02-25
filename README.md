# HyBot

An interactive AI coding assistant in your terminal, powered by the [agno](https://github.com/agno-agi/agno) framework.

一个运行在终端的交互式 AI 编码助手，基于 [agno](https://github.com/agno-agi/agno) 框架构建。

---

## Features / 功能特性

- **Multi-provider support / 多模型 Provider 支持** — OpenAI Chat Completions, OpenAI Responses API, Anthropic Claude, Google Gemini
- **Built-in tools / 内置工具** — File read/write, shell commands (CodingTools), Python execution (PythonTools)
- **MCP integration / MCP 集成** — Connect to any [Model Context Protocol](https://modelcontextprotocol.io/) server via stdio or HTTP
- **Skills system / 技能系统** — Modular, reusable skill packages loaded from a configurable directory
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

# Launch / 启动
hybot

# Resume a previous session / 恢复历史会话
hybot --session <session-id>

# Use a custom config file / 指定配置文件
hybot --config /path/to/config.yaml
```

On first run in a directory, HyBot will ask for workspace trust approval and initialize a `.hybot/` directory.

首次在某目录运行时，HyBot 会请求工作区信任授权并初始化 `.hybot/` 目录。

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
| `/exit` | Exit HyBot / 退出 |

You can also type `exit`, `quit`, or `bye` to leave, or press `Ctrl+C`.

也可以输入 `exit`、`quit`、`bye` 或按 `Ctrl+C` 退出。

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

---

## Skills / 技能

Place skill packages in the skills directory (`~/.hybot/skills/` by default). HyBot discovers and loads them automatically at startup.

将技能包放入技能目录（默认为 `~/.hybot/skills/`），HyBot 在启动时自动发现并加载。

See `skills/weather/` and `skills/fetch_markdown/` for examples.

参考 `skills/weather/` 和 `skills/fetch_markdown/` 了解编写方式。

---

## Project Structure / 项目结构

```
├── src/hybot/
│   ├── __main__.py     # CLI entry point / CLI 入口
│   ├── agent.py        # Agent builder & interactive loop / Agent 构建与交互循环
│   ├── commands.py     # Slash command registry / 斜杠命令注册
│   └── config.py       # Config models & loading / 配置模型与加载
├── skills/             # Example skill packages / 示例技能包
├── config.yaml         # Default config / 默认配置
└── pyproject.toml      # Package metadata / 包元数据
```

---

## License / 许可证

MIT
