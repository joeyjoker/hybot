"""Skill 和 MCP 生命周期管理。"""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from hybot.config import HYBOT_HOME

console = Console()


# ---------------------------------------------------------------------------
# Skill 操作
# ---------------------------------------------------------------------------


def list_skills(global_skills_dir: Path, project_skills_dir: Path | None) -> None:
    """列出全局库和项目中的 skill。"""
    table = Table(title="Skills", show_header=True, header_style="bold cyan")
    table.add_column("名称", style="green")
    table.add_column("位置")
    table.add_column("状态")

    global_names: set[str] = set()
    if global_skills_dir.is_dir():
        for item in sorted(global_skills_dir.iterdir()):
            if item.is_file() and item.suffix in (".md", ".txt", ".yaml"):
                name = item.stem
                global_names.add(name)
                in_project = (
                    project_skills_dir
                    and (project_skills_dir / item.name).exists()
                )
                status = "[green]已安装到项目[/green]" if in_project else "[dim]仅全局[/dim]"
                table.add_row(name, "全局", status)

    if project_skills_dir and project_skills_dir.is_dir():
        for item in sorted(project_skills_dir.iterdir()):
            if item.is_file() and item.stem not in global_names:
                table.add_row(item.stem, "项目", "[cyan]本地[/cyan]")

    console.print(table)


def install_skill(name: str, global_skills_dir: Path, project_skills_dir: Path) -> bool:
    """从全局库复制 skill 到项目目录。"""
    # 查找全局 skill 文件
    source = None
    if global_skills_dir.is_dir():
        for item in global_skills_dir.iterdir():
            if item.stem == name:
                source = item
                break

    if source is None:
        console.print(f"[red]未在全局库中找到 skill '{name}'。[/red]")
        return False

    project_skills_dir.mkdir(parents=True, exist_ok=True)
    dest = project_skills_dir / source.name
    shutil.copy2(source, dest)
    console.print(f"[green]已安装 skill '{name}' 到项目。[/green]")
    return True


def remove_skill(name: str, project_skills_dir: Path) -> bool:
    """从项目目录移除 skill。"""
    if not project_skills_dir or not project_skills_dir.is_dir():
        console.print("[red]项目中没有 skills 目录。[/red]")
        return False

    removed = False
    for item in project_skills_dir.iterdir():
        if item.stem == name:
            item.unlink()
            removed = True

    if removed:
        console.print(f"[green]已从项目中移除 skill '{name}'。[/green]")
    else:
        console.print(f"[red]项目中未找到 skill '{name}'。[/red]")
    return removed


def catalog_skill(name: str, project_skills_dir: Path, global_skills_dir: Path) -> bool:
    """将项目中的 skill 上报到全局库。"""
    if not project_skills_dir or not project_skills_dir.is_dir():
        console.print("[red]项目中没有 skills 目录。[/red]")
        return False

    source = None
    for item in project_skills_dir.iterdir():
        if item.stem == name:
            source = item
            break

    if source is None:
        console.print(f"[red]项目中未找到 skill '{name}'。[/red]")
        return False

    global_skills_dir.mkdir(parents=True, exist_ok=True)
    dest = global_skills_dir / source.name
    shutil.copy2(source, dest)
    console.print(f"[green]已将 skill '{name}' 上报到全局库。[/green]")
    return True


# ---------------------------------------------------------------------------
# MCP 操作
# ---------------------------------------------------------------------------

MCP_REGISTRY_FILE = HYBOT_HOME / "mcp_registry.yaml"


def _load_mcp_registry() -> dict:
    """加载全局 MCP 注册表。"""
    if not MCP_REGISTRY_FILE.exists():
        return {}
    with open(MCP_REGISTRY_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_mcp_servers(config_mcp_servers: list) -> None:
    """列出已配置的 MCP 服务。"""
    table = Table(title="MCP 服务", show_header=True, header_style="bold cyan")
    table.add_column("名称", style="green")
    table.add_column("类型")
    table.add_column("地址/命令")

    for srv in config_mcp_servers:
        srv_type = "command" if srv.command else "url"
        addr = srv.command or srv.url or "-"
        table.add_row(srv.name, srv_type, addr)

    if not config_mcp_servers:
        console.print("[yellow]当前没有配置 MCP 服务。[/yellow]")
        return

    console.print(table)

    # 显示注册表中可用但未配置的
    registry = _load_mcp_registry()
    available = registry.get("servers", {})
    configured_names = {s.name for s in config_mcp_servers}
    not_configured = [n for n in available if n not in configured_names]
    if not_configured:
        console.print(f"\n[dim]注册表中可用: {', '.join(not_configured)}[/dim]")


def add_mcp_server(name: str, workspace: Path) -> bool:
    """从 mcp_registry.yaml 注册 MCP 服务到项目 config。"""
    registry = _load_mcp_registry()
    available = registry.get("servers", {})

    if name not in available:
        console.print(f"[red]注册表中未找到 MCP 服务 '{name}'。[/red]")
        if available:
            console.print(f"[dim]可用: {', '.join(available.keys())}[/dim]")
        return False

    server_def = available[name]
    local_config_path = workspace / ".hybot" / "config.yaml"

    # 读取现有本地配置
    local_data: dict = {}
    if local_config_path.exists():
        with open(local_config_path, encoding="utf-8") as f:
            local_data = yaml.safe_load(f) or {}

    mcp_list = local_data.setdefault("mcp_servers", [])
    # 检查是否已存在
    for srv in mcp_list:
        if srv.get("name") == name:
            console.print(f"[yellow]MCP 服务 '{name}' 已存在于项目配置中。[/yellow]")
            return False

    entry = {"name": name}
    entry.update(server_def)
    mcp_list.append(entry)

    local_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(local_config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(local_data, f, allow_unicode=True, default_flow_style=False)

    console.print(f"[green]已将 MCP 服务 '{name}' 添加到项目配置。需重启 hybot 生效。[/green]")
    return True


def remove_mcp_server(name: str, workspace: Path) -> bool:
    """从项目 config 中移除 MCP 服务。"""
    local_config_path = workspace / ".hybot" / "config.yaml"

    if not local_config_path.exists():
        console.print("[red]项目中没有本地配置文件。[/red]")
        return False

    with open(local_config_path, encoding="utf-8") as f:
        local_data = yaml.safe_load(f) or {}

    mcp_list = local_data.get("mcp_servers", [])
    new_list = [s for s in mcp_list if s.get("name") != name]

    if len(new_list) == len(mcp_list):
        console.print(f"[red]项目配置中未找到 MCP 服务 '{name}'。[/red]")
        return False

    local_data["mcp_servers"] = new_list
    with open(local_config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(local_data, f, allow_unicode=True, default_flow_style=False)

    console.print(f"[green]已从项目配置中移除 MCP 服务 '{name}'。需重启 hybot 生效。[/green]")
    return True
