"""Agent 构建与交互式 CLI 循环。"""

from __future__ import annotations

import contextlib
from pathlib import Path

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.tools.coding import CodingTools
from agno.tools.mcp import MCPTools
from agno.tools.python import PythonTools
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML

from hybot.commands import COMMANDS, CommandContext, handle_slash_command
from hybot.config import AppConfig, load_agent_md


class SlashCompleter(Completer):
    """斜杠命令与 Skill 自动补全。"""

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
        # 已有空格说明在输入参数，不再补全命令名
        if " " in word:
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


async def build_and_run(
    config: AppConfig,
    session_id: str | None = None,
    workspace: Path | None = None,
) -> None:
    """构建 Agent 并启动交互式 CLI 循环。"""

    # 1. 构建 Model
    model = _build_model(config)

    # 2. 构建内置工具列表
    tools: list = []
    if config.tools.coding.enabled:
        tools.append(
            CodingTools(
                base_dir=config.tools.coding.base_dir,
                all=config.tools.coding.all,
            )
        )
    if config.tools.python.enabled:
        tools.append(PythonTools())

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

    # 4. 构建 Skills（可选）
    skills = None
    if config.skills.path:
        from agno.skills import LocalSkills, Skills

        skills_path = str(Path(config.skills.path).expanduser())
        Path(skills_path).mkdir(parents=True, exist_ok=True)
        skills = Skills(loaders=[LocalSkills(path=skills_path)])

    # 5. 构建 Storage
    db = None
    if config.storage.type == "sqlite":
        db_file = str(Path(config.storage.db_file).expanduser())
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
        db = SqliteDb(db_file=db_file)

    # 6. 使用 AsyncExitStack 管理 MCP 连接生命周期
    async with contextlib.AsyncExitStack() as stack:
        for mcp in mcp_tools:
            await stack.enter_async_context(mcp)

        all_tools = tools + mcp_tools

        # 读取 AGENT.md 指令并追加到 instructions
        agent_md_instructions = load_agent_md(workspace or Path.cwd())
        all_instructions = list(config.agent.instructions) + agent_md_instructions

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
        )

        # 自定义 CLI 循环（支持斜杠命令拦截）
        ctx = CommandContext(
            config=config,
            workspace=workspace or Path.cwd(),
            db=db,
            skills=skills,
            agent=agent,
            show_reasoning=config.agent.show_reasoning,
        )

        # 构建自动补全器
        skill_entries: list[tuple[str, str]] = []
        if skills:
            for s in skills.get_all_skills():
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
                continue

            await agent.aprint_response(
                message,
                stream=config.agent.stream,
                markdown=config.agent.markdown,
                show_reasoning=ctx.show_reasoning,
            )
