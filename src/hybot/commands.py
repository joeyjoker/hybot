"""斜杠命令注册与处理。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Awaitable

import yaml
from rich.console import Console
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.skills import Skills

from hybot.config import AppConfig, init_workspace

console = Console()


@dataclass
class CommandContext:
    """斜杠命令处理所需的上下文依赖。"""

    config: AppConfig
    workspace: Path
    db: SqliteDb | None
    skills: Skills | None
    agent: Agent
    show_reasoning: bool = True


@dataclass
class SlashCommand:
    """斜杠命令定义。"""

    name: str
    description: str
    handler: Callable[[CommandContext], Awaitable[None]]


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------


async def cmd_help(ctx: CommandContext) -> None:
    """显示所有可用命令。"""
    table = Table(title="可用命令", show_header=True, header_style="bold cyan")
    table.add_column("命令", style="green")
    table.add_column("说明")
    for cmd in COMMANDS.values():
        table.add_row(f"/{cmd.name}", cmd.description)
    # 将 Skills 也列入命令表
    if ctx.skills:
        for skill in ctx.skills.get_all_skills():
            table.add_row(
                f"/{skill.name}",
                f"[dim](Skill)[/dim] {skill.description or '-'}",
            )
    console.print(table)


async def cmd_resume(ctx: CommandContext) -> None:
    """列出最近会话，选择恢复。"""
    if ctx.db is None:
        console.print("[yellow]未配置存储，无法恢复会话。[/yellow]")
        return

    from agno.db.base import SessionType

    try:
        sessions = ctx.db.get_sessions(
            session_type=SessionType.AGENT,
            limit=10,
            sort_order="desc",
            sort_by="created_at",
        )
    except Exception as e:
        console.print(f"[red]获取会话列表失败：{e}[/red]")
        return

    if not sessions:
        console.print("[yellow]没有历史会话。[/yellow]")
        return

    table = Table(title="最近会话", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Session ID", style="green")
    table.add_column("创建时间")
    table.add_column("会话名称")

    for idx, session in enumerate(sessions, 1):
        created = ""
        if session.created_at:
            created = datetime.fromtimestamp(
                session.created_at, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
        name = ""
        if session.session_data and isinstance(session.session_data, dict):
            name = session.session_data.get("session_name", "")
        table.add_row(str(idx), session.session_id[:12] + "...", created, name or "-")

    console.print(table)

    choice = Prompt.ask("输入序号恢复会话（回车取消）", default="")
    if not choice:
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(sessions):
            selected = sessions[idx]
            ctx.agent.session_id = selected.session_id
            console.print(
                f"[green]已恢复会话：{selected.session_id[:12]}...[/green]"
            )
        else:
            console.print("[red]无效序号。[/red]")
    except ValueError:
        console.print("[red]请输入有效数字。[/red]")


async def cmd_init(ctx: CommandContext) -> None:
    """重新初始化当前工作区。"""
    init_workspace(ctx.workspace)
    console.print(f"[green]工作区已初始化：{ctx.workspace}[/green]")


async def cmd_skills(ctx: CommandContext) -> None:
    """列出可用 Skills 并选择查看。"""
    if ctx.skills is None:
        console.print("[yellow]未配置 Skills。[/yellow]")
        return

    all_skills = ctx.skills.get_all_skills()
    if not all_skills:
        console.print("[yellow]没有可用的 Skill。[/yellow]")
        return

    table = Table(title="可用 Skills", show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("名称", style="green")
    table.add_column("说明")

    for idx, skill in enumerate(all_skills, 1):
        table.add_row(str(idx), skill.name, skill.description or "-")

    console.print(table)

    choice = Prompt.ask("输入序号查看详情（回车取消）", default="")
    if not choice:
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_skills):
            skill = all_skills[idx]
            console.print(f"\n[bold cyan]{skill.name}[/bold cyan]")
            if skill.description:
                console.print(f"[dim]{skill.description}[/dim]\n")
            if skill.instructions:
                console.print(skill.instructions)
        else:
            console.print("[red]无效序号。[/red]")
    except ValueError:
        console.print("[red]请输入有效数字。[/red]")


async def cmd_config(ctx: CommandContext) -> None:
    """显示当前合并后的配置。"""
    config_dict = ctx.config.model_dump()
    # 隐藏敏感字段
    if config_dict.get("model", {}).get("api_key"):
        config_dict["model"]["api_key"] = "***"
    yaml_str = yaml.dump(config_dict, allow_unicode=True, default_flow_style=False, sort_keys=False)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
    console.print(syntax)


async def cmd_reasoning(ctx: CommandContext) -> None:
    """切换 Agent 推理（reasoning）能力。"""
    ctx.agent.reasoning = not ctx.agent.reasoning
    status = "[green]已开启[/green]" if ctx.agent.reasoning else "[yellow]已关闭[/yellow]"
    console.print(f"Reasoning 能力：{status}")


async def cmd_thinking(ctx: CommandContext) -> None:
    """切换思考过程的显示。"""
    ctx.show_reasoning = not ctx.show_reasoning
    status = "[green]显示[/green]" if ctx.show_reasoning else "[yellow]隐藏[/yellow]"
    console.print(f"思考过程：{status}")


async def cmd_exit(ctx: CommandContext) -> None:
    """退出 CLI。"""
    raise SystemExit(0)


# ---------------------------------------------------------------------------
# 命令注册表
# ---------------------------------------------------------------------------

COMMANDS: dict[str, SlashCommand] = {}


def _register(name: str, description: str, handler: Callable[[CommandContext], Awaitable[None]]) -> None:
    COMMANDS[name] = SlashCommand(name=name, description=description, handler=handler)


_register("help", "显示所有可用命令", cmd_help)
_register("resume", "列出最近会话，选择恢复", cmd_resume)
_register("init", "重新初始化当前工作区", cmd_init)
_register("skills", "列出可用 Skills 并选择执行", cmd_skills)
_register("config", "显示当前合并后的配置", cmd_config)
_register("reasoning", "开关 Reasoning 推理能力", cmd_reasoning)
_register("thinking", "开关思考过程显示", cmd_thinking)
_register("exit", "退出 CLI", cmd_exit)


# ---------------------------------------------------------------------------
# 命令分发
# ---------------------------------------------------------------------------


async def handle_slash_command(user_input: str, ctx: CommandContext) -> None:
    """判断并处理斜杠命令。

    优先匹配内置命令，其次匹配 Skill 名称。
    如果输入是 ``/`` 或 ``/help``，打印帮助。
    """
    stripped = user_input.strip()

    # 单独 "/" 等同于 "/help"
    if stripped == "/":
        await cmd_help(ctx)
        return

    # 提取命令名（去掉 "/" 前缀，取第一个 token）
    parts = stripped[1:].split(maxsplit=1)
    cmd_name = parts[0].lower()

    # 1. 匹配内置命令
    if cmd_name in COMMANDS:
        await COMMANDS[cmd_name].handler(ctx)
        return

    # 2. 匹配 Skill 名称，通过 Agent 调用
    if ctx.skills:
        for skill in ctx.skills.get_all_skills():
            if skill.name.lower() == cmd_name:
                args = parts[1] if len(parts) > 1 else ""
                prompt = f"请使用 {skill.name} 技能"
                if args:
                    prompt += f"：{args}"
                await ctx.agent.aprint_response(
                    prompt,
                    stream=ctx.config.agent.stream,
                    markdown=ctx.config.agent.markdown,
                    show_reasoning=ctx.show_reasoning,
                )
                return

    console.print(f"[red]未知命令：/{cmd_name}[/red]")
    console.print("输入 [green]/help[/green] 查看所有可用命令。")
