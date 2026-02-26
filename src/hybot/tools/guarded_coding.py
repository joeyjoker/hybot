"""带危险操作确认的 CodingTools 子类。"""

from __future__ import annotations

import re
from typing import Optional

from agno.tools.coding import CodingTools
from rich.console import Console
from rich.prompt import Confirm

console = Console()

# 危险 shell 命令模式
DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"\brm\s+(-[a-zA-Z]*[rf]|--force|--recursive)\b"),
    re.compile(r"\brm\b.*\s+/"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bchmod\b"),
    re.compile(r"\bchown\b"),
    re.compile(r"\bdd\b"),
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bfdisk\b"),
    re.compile(r"\bformat\b"),
    re.compile(r"\b(shutdown|reboot|poweroff|halt)\b"),
    re.compile(r"\bgit\s+push\s+.*--force"),
    re.compile(r"\bgit\s+reset\s+--hard"),
    re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f"),
    re.compile(r">\s*/dev/"),
    re.compile(r"\bkill\s+-9"),
    re.compile(r"\bkillall\b"),
    re.compile(r"\bpkill\b"),
]


def _is_dangerous(command: str) -> bool:
    """检查命令是否匹配危险模式。"""
    return any(p.search(command) for p in DANGEROUS_PATTERNS)


def _confirm_action(action_desc: str, detail: str = "") -> bool:
    """弹出确认提示，返回用户是否同意。"""
    console.print(f"\n[bold yellow]!! 危险操作确认[/bold yellow]")
    console.print(f"  操作: [bold]{action_desc}[/bold]")
    if detail:
        console.print(f"  详情: [dim]{detail[:200]}[/dim]")
    return Confirm.ask("  是否继续？", default=False)


class GuardedCodingTools(CodingTools):
    """带危险操作确认的 CodingTools。

    三种模式：
    - "dangerous"（默认）：仅对危险 shell 命令确认
    - "always"：所有 shell 命令和文件写入都确认
    - "never"：不确认
    """

    def __init__(self, approval_mode: str = "dangerous", **kwargs):
        super().__init__(**kwargs)
        self.approval_mode = approval_mode

    def run_shell(self, command: str, timeout: Optional[int] = None) -> str:
        """执行 shell 命令，根据 approval_mode 可能弹出确认。"""
        if self.approval_mode == "always":
            if not _confirm_action("执行 Shell 命令", command):
                return "Error: Operation rejected by user."
        elif self.approval_mode == "dangerous" and _is_dangerous(command):
            if not _confirm_action("执行危险 Shell 命令", command):
                return "Error: Operation rejected by user."
        return super().run_shell(command, timeout=timeout)

    def write_file(self, file_path: str, contents: str) -> str:
        """写入文件，在 always 模式下弹出确认。"""
        if self.approval_mode == "always":
            if not _confirm_action("写入文件", file_path):
                return "Error: Operation rejected by user."
        return super().write_file(file_path, contents)

    def edit_file(self, file_path: str, old_text: str, new_text: str) -> str:
        """编辑文件，在 always 模式下弹出确认。"""
        if self.approval_mode == "always":
            if not _confirm_action("编辑文件", file_path):
                return "Error: Operation rejected by user."
        return super().edit_file(file_path, old_text, new_text)
