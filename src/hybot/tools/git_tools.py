"""Git 工具：封装 git CLI 调用。"""

from __future__ import annotations

import subprocess
from typing import Optional

from agno.tools import Toolkit


class GitTools(Toolkit):
    """Git 操作工具集，通过 subprocess 调用 git CLI。"""

    def __init__(self, base_dir: str = "."):
        super().__init__(name="git_tools")
        self.base_dir = base_dir
        self.register(self.git_status)
        self.register(self.git_diff)
        self.register(self.git_log)
        self.register(self.git_add)
        self.register(self.git_commit)
        self.register(self.git_branch)
        self.register(self.git_checkout)
        self.register(self.git_stash)
        self.register(self.git_show)

    def _run(self, args: list[str], timeout: int = 30) -> str:
        """执行 git 命令并返回输出。"""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout
            if result.returncode != 0:
                output += f"\n[stderr] {result.stderr}" if result.stderr else ""
                output = f"[exit code {result.returncode}]\n{output}"
            return output.strip()
        except FileNotFoundError:
            return "Error: git 未安装或不在 PATH 中。"
        except subprocess.TimeoutExpired:
            return "Error: git 命令执行超时。"

    def git_status(self) -> str:
        """查看当前工作树状态（git status）。"""
        return self._run(["status"])

    def git_diff(self, cached: bool = False, file_path: Optional[str] = None) -> str:
        """查看差异。

        Args:
            cached: 如果为 True，查看暂存区的差异（--cached）
            file_path: 可选，限定查看特定文件的差异
        """
        args = ["diff"]
        if cached:
            args.append("--cached")
        if file_path:
            args.extend(["--", file_path])
        return self._run(args)

    def git_log(self, max_entries: int = 10, oneline: bool = True) -> str:
        """查看提交历史。

        Args:
            max_entries: 最多显示的提交数量，默认 10
            oneline: 是否使用单行格式，默认 True
        """
        args = ["log", f"-{max_entries}"]
        if oneline:
            args.append("--oneline")
        return self._run(args)

    def git_add(self, paths: str) -> str:
        """将文件添加到暂存区。

        Args:
            paths: 要暂存的文件路径，多个路径用空格分隔。使用 '.' 表示所有文件。
        """
        path_list = paths.split()
        return self._run(["add"] + path_list)

    def git_commit(self, message: str) -> str:
        """创建一个新的提交。

        Args:
            message: 提交消息
        """
        return self._run(["commit", "-m", message])

    def git_branch(self, create: Optional[str] = None, delete: Optional[str] = None) -> str:
        """分支管理。无参数时列出所有分支。

        Args:
            create: 要创建的新分支名
            delete: 要删除的分支名
        """
        if create:
            return self._run(["branch", create])
        if delete:
            return self._run(["branch", "-d", delete])
        return self._run(["branch", "-a"])

    def git_checkout(self, ref: str, create: bool = False) -> str:
        """切换分支或恢复文件。

        Args:
            ref: 分支名、标签或提交哈希
            create: 如果为 True，创建并切换到新分支（-b）
        """
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(ref)
        return self._run(args)

    def git_stash(self, action: str = "list", message: Optional[str] = None) -> str:
        """储藏管理。

        Args:
            action: 操作类型 - "push"（储藏）, "pop"（恢复最近）, "list"（列出）, "drop"（丢弃最近）
            message: 储藏时的说明消息（仅 push 时有效）
        """
        if action == "push":
            args = ["stash", "push"]
            if message:
                args.extend(["-m", message])
            return self._run(args)
        if action in ("pop", "list", "drop"):
            return self._run(["stash", action])
        return f"Error: 不支持的 stash 操作 '{action}'。支持: push, pop, list, drop"

    def git_show(self, ref: str = "HEAD") -> str:
        """查看指定提交的详情。

        Args:
            ref: 提交引用，默认 HEAD
        """
        return self._run(["show", ref, "--stat"])
