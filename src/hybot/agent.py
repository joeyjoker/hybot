"""Agent 构建与交互式 CLI 循环。"""

from __future__ import annotations

import contextlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.tools.mcp import MCPTools
from agno.tools.python import PythonTools
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

from hybot.commands import COMMANDS, CommandContext, handle_slash_command
from hybot.config import AppConfig, load_agent_md
from hybot.memory import MemoryStore, MemoryTools
from hybot.project_scanner import load_or_scan
from hybot.tools.guarded_coding import GuardedCodingTools


SUBCOMMANDS: dict[str, list[tuple[str, str]]] = {
    "skill": [
        ("list", "列出所有 skill"),
        ("install", "从全局库安装 skill"),
        ("remove", "从项目移除 skill"),
        ("catalog", "将 skill 上报到全局库"),
    ],
    "mcp": [
        ("list", "列出 MCP 服务"),
        ("add", "添加 MCP 服务"),
        ("remove", "移除 MCP 服务"),
    ],
    "project": [
        ("rescan", "强制重新扫描项目"),
    ],
}


class SlashCompleter(Completer):
    """斜杠命令与 Skill 自动补全，支持子命令。"""

    def __init__(
        self,
        commands: dict,
        skill_entries: list[tuple[str, str]],
    ):
        self.commands = commands
        self.skill_entries = skill_entries  # [(name, description), ...]

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        word = text[1:]

        if " " in word:
            # 子命令补全
            cmd_name, sub_word = word.split(maxsplit=1)
            # 如果 sub_word 中还有空格，说明已经输完子命令了
            if " " in sub_word:
                return
            subcmds = SUBCOMMANDS.get(cmd_name, [])
            for sub_name, sub_desc in subcmds:
                if sub_name.startswith(sub_word):
                    yield Completion(
                        sub_name,
                        start_position=-len(sub_word),
                        display_meta=sub_desc,
                    )
            return

        for name, cmd in self.commands.items():
            if name.startswith(word):
                yield Completion(
                    name,
                    start_position=-len(word),
                    display_meta=cmd.description,
                )
        for skill_name, skill_desc in self.skill_entries:
            if skill_name.startswith(word):
                yield Completion(
                    skill_name,
                    start_position=-len(word),
                    display_meta=f"(Skill) {skill_desc}",
                )


def _build_model(config: AppConfig):
    """根据 config.model.provider 构建对应的 Model 实例。"""
    provider = config.model.provider
    common: dict = {"id": config.model.id}
    if config.model.api_key:
        common["api_key"] = config.model.api_key

    if provider == "openai":
        from agno.models.openai import OpenAIChat
        if config.model.reasoning_effort:
            common["reasoning_effort"] = config.model.reasoning_effort
        return OpenAIChat(**common, base_url=config.model.base_url)

    if provider == "openai_responses":
        from agno.models.openai import OpenAIResponses
        if config.model.reasoning_effort:
            common["reasoning_effort"] = config.model.reasoning_effort
        if config.model.reasoning_summary:
            common["reasoning_summary"] = config.model.reasoning_summary
        return OpenAIResponses(**common, base_url=config.model.base_url)

    if provider == "anthropic":
        from agno.models.anthropic import Claude
        return Claude(**common)

    if provider == "gemini":
        from agno.models.google import Gemini
        return Gemini(**common)

    raise ValueError(f"不支持的 model provider: {provider}")


@dataclass
class AgentStack:
    """Agent 构建产物，便于在不同模式间共享。"""

    agent: Agent
    memory_store: MemoryStore | None
    db: SqliteDb | None
    skills: Any
    mcp_tools: list[MCPTools]


async def _build_agent_stack(
    config: AppConfig,
    workspace: Path,
    session_id: str | None = None,
    exit_stack: contextlib.AsyncExitStack | None = None,
) -> AgentStack:
    """构建 Agent 及其所有依赖，返回 AgentStack。"""

    # 1. 构建 Model
    model = _build_model(config)

    # 2. 构建内置工具列表
    tools: list = []
    if config.tools.coding.enabled:
        tools.append(
            GuardedCodingTools(
                approval_mode=config.approval.mode,
                base_dir=config.tools.coding.base_dir,
                all=config.tools.coding.all,
            )
        )
    if config.tools.python.enabled:
        tools.append(PythonTools())

    # 2a. 记忆工具
    memory_store: MemoryStore | None = None
    if config.memory.enabled:
        memory_store = MemoryStore(path=config.memory.path)
        tools.append(MemoryTools(store=memory_store))

    # 2b. Git 工具
    if config.tools.git.enabled:
        from hybot.tools.git_tools import GitTools
        tools.append(GitTools(base_dir=str(workspace)))

    # 2c. Web 工具
    if config.tools.web.enabled:
        try:
            if config.tools.web.enable_search:
                from agno.tools.duckduckgo import DuckDuckGoTools
                tools.append(DuckDuckGoTools())
            if config.tools.web.enable_fetch:
                from agno.tools.website import WebsiteTools
                tools.append(WebsiteTools())
        except ImportError:
            pass  # web 依赖未安装时静默跳过

    # 2d. Sub-agent 工具
    from hybot.subagent import SubAgentTools, load_subagent_configs
    subagent_configs = load_subagent_configs(workspace)
    if subagent_configs:
        tools.append(SubAgentTools(subagent_configs, workspace))

    # 3. 构建 MCP 工具列表
    mcp_tools: list[MCPTools] = []
    for mcp_cfg in config.mcp_servers:
        if mcp_cfg.command:
            mcp_tools.append(MCPTools(command=mcp_cfg.command, env=mcp_cfg.env))
        elif mcp_cfg.url:
            mcp_tools.append(
                MCPTools(
                    url=mcp_cfg.url,
                    transport=mcp_cfg.transport or "streamable-http",
                )
            )

    if exit_stack:
        for mcp in mcp_tools:
            await exit_stack.enter_async_context(mcp)

    all_tools = tools + mcp_tools

    # 4. 构建 Skills（内置默认 + 全局 + 项目本地）
    skills = None
    from agno.skills import LocalSkills, Skills

    loaders: list = []
    # 4a. 内置默认 skills（随包分发）
    default_skills_dir = Path(__file__).parent / "default_skills"
    if default_skills_dir.is_dir():
        loaders.append(LocalSkills(path=str(default_skills_dir)))
    # 4b. 全局 skills 目录（validate=False 避免无效 skill 导致全部加载失败）
    if config.skills.path:
        skills_path = str(Path(config.skills.path).expanduser())
        Path(skills_path).mkdir(parents=True, exist_ok=True)
        loaders.append(LocalSkills(path=skills_path, validate=False))
    # 4c. 项目本地 skills 目录
    project_skills_dir = workspace / ".hybot" / "skills"
    if project_skills_dir.is_dir():
        loaders.append(LocalSkills(path=str(project_skills_dir), validate=False))
    if loaders:
        try:
            skills = Skills(loaders=loaders)
        except Exception as e:
            import logging
            logging.warning(f"Skills 加载失败（已跳过）: {e}")

    # 5. 构建 Storage
    db = None
    if config.storage.type == "sqlite":
        db_file = str(Path(config.storage.db_file).expanduser())
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
        db = SqliteDb(db_file=db_file)

    # 6. 组装 instructions
    agent_md_instructions = load_agent_md(workspace)
    all_instructions = list(config.agent.instructions) + agent_md_instructions

    # 7. 组装 additional_context：记忆 + 项目信息
    context_parts: list[str] = []
    if memory_store:
        memory_content = memory_store.load_all()
        if memory_content:
            context_parts.append(f"## Persistent Memory\n{memory_content}")
    if config.project.scan_on_startup:
        project_info = load_or_scan(workspace, cache=config.project.cache_scan)
        if project_info:
            context_parts.append(f"## Project Context\n{project_info}")
    additional_context = "\n\n".join(context_parts) or None

    # 8. 构建 Agent
    agent = Agent(
        model=model,
        name=config.agent.name,
        description=config.agent.description,
        instructions=all_instructions,
        tools=all_tools,
        skills=skills,
        db=db,
        markdown=config.agent.markdown,
        stream=config.agent.stream,
        reasoning=config.agent.reasoning,
        add_history_to_context=config.agent.add_history_to_context,
        num_history_runs=config.agent.num_history_runs,
        add_datetime_to_context=config.agent.add_datetime_to_context,
        session_id=session_id,
        additional_context=additional_context,
    )

    return AgentStack(
        agent=agent,
        memory_store=memory_store,
        db=db,
        skills=skills,
        mcp_tools=mcp_tools,
    )


async def build_and_run(
    config: AppConfig,
    session_id: str | None = None,
    workspace: Path | None = None,
) -> None:
    """构建 Agent 并启动交互式 CLI 循环。"""
    ws = workspace or Path.cwd()

    async with contextlib.AsyncExitStack() as stack:
        st = await _build_agent_stack(config, ws, session_id=session_id, exit_stack=stack)

        # 自定义 CLI 循环（支持斜杠命令拦截）
        ctx = CommandContext(
            config=config,
            workspace=ws,
            db=st.db,
            skills=st.skills,
            agent=st.agent,
            show_reasoning=config.agent.show_reasoning,
            memory_store=st.memory_store,
        )

        # 构建自动补全器
        skill_entries: list[tuple[str, str]] = []
        if st.skills:
            for s in st.skills.get_all_skills():
                skill_entries.append((s.name, s.description or ""))
        completer = SlashCompleter(COMMANDS, skill_entries)
        prompt_session: PromptSession[str] = PromptSession(
            completer=completer,
            complete_while_typing=True,
        )

        while True:
            try:
                message = await prompt_session.prompt_async(
                    HTML("<b>&gt; User </b>"),
                )
            except (KeyboardInterrupt, EOFError):
                break

            if not message or not message.strip():
                continue
            if message.strip() in ("exit", "quit", "bye"):
                break
            if message.strip().startswith("/"):
                try:
                    await handle_slash_command(message, ctx)
                except SystemExit:
                    break
                except KeyboardInterrupt:
                    print("\n[已中断]")
                continue

            try:
                await st.agent.aprint_response(
                    message,
                    stream=config.agent.stream,
                    markdown=config.agent.markdown,
                    show_reasoning=ctx.show_reasoning,
                )
            except KeyboardInterrupt:
                print("\n[已中断]")

            # 每次回复后 reload skills，使新创建的 skill 立刻可用
            if st.skills:
                try:
                    st.skills.reload()
                except Exception:
                    pass


async def build_and_run_once(
    config: AppConfig,
    task: str,
    workspace: Path | None = None,
    output_format: str = "text",
) -> int:
    """非交互模式：执行单个任务后退出，返回 exit code。"""
    ws = workspace or Path.cwd()

    async with contextlib.AsyncExitStack() as stack:
        st = await _build_agent_stack(config, ws, exit_stack=stack)

        try:
            if output_format == "json":
                # JSON 模式：先执行任务
                response = await st.agent.arun(task)
                # 再让 Agent 总结为结构化输出
                from hybot.schemas import RunSummary
                summary_prompt = (
                    "请根据你刚才执行的任务结果，生成一个 JSON 格式的总结，包含以下字段：\n"
                    '- status: "success" 或 "error" 或 "partial"\n'
                    "- summary: 简短总结\n"
                    "- files_modified: 修改的文件列表\n"
                    "- files_created: 创建的文件列表\n"
                    "- commands_run: 执行的命令列表\n"
                    "- errors: 错误列表\n"
                    "只输出 JSON，不要其他内容。"
                )
                summary_response = await st.agent.arun(summary_prompt)
                # 尝试从回复中提取 JSON
                content = summary_response.content if summary_response else ""
                try:
                    # 尝试从 markdown code block 中提取
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    data = json.loads(content.strip())
                    summary = RunSummary(**data)
                except (json.JSONDecodeError, IndexError, ValueError):
                    summary = RunSummary(
                        status="success",
                        summary=content[:500] if content else "任务已完成。",
                    )
                print(summary.model_dump_json(indent=2))
            else:
                # Text 模式：直接流式输出
                await st.agent.aprint_response(
                    task,
                    stream=config.agent.stream,
                    markdown=config.agent.markdown,
                )
            return 0
        except Exception as e:
            if output_format == "json":
                from hybot.schemas import RunSummary
                summary = RunSummary(status="error", errors=[str(e)])
                print(summary.model_dump_json(indent=2), file=sys.stderr)
            else:
                print(f"Error: {e}", file=sys.stderr)
            return 1
