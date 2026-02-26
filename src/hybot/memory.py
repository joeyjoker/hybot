"""持久记忆系统：管理 ~/.hybot/memory/ 目录下的 md 文件。"""

from __future__ import annotations

from pathlib import Path

from agno.tools import Toolkit


class MemoryStore:
    """管理持久记忆文件的读写。"""

    def __init__(self, path: str = "~/.hybot/memory"):
        self.base_dir = Path(path).expanduser()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _category_path(self, category: str) -> Path:
        safe_name = category.replace("/", "_").replace("\\", "_")
        if not safe_name.endswith(".md"):
            safe_name += ".md"
        return self.base_dir / safe_name

    def load_all(self) -> str:
        """读取所有 md 文件，拼接为上下文文本。"""
        parts: list[str] = []
        for md_file in sorted(self.base_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8").strip()
            if content:
                category = md_file.stem
                parts.append(f"### {category}\n{content}")
        return "\n\n".join(parts)

    def save(self, category: str, content: str) -> None:
        """写入指定分类的 md 文件。"""
        path = self._category_path(category)
        path.write_text(content.strip() + "\n", encoding="utf-8")

    def list_entries(self) -> dict[str, str]:
        """列出所有分类及内容摘要（前 200 字符）。"""
        entries: dict[str, str] = {}
        for md_file in sorted(self.base_dir.glob("*.md")):
            content = md_file.read_text(encoding="utf-8").strip()
            entries[md_file.stem] = content[:200] + ("..." if len(content) > 200 else "")
        return entries

    def delete(self, category: str) -> bool:
        """删除指定分类，返回是否成功。"""
        path = self._category_path(category)
        if path.exists():
            path.unlink()
            return True
        return False


class MemoryTools(Toolkit):
    """暴露给 Agent 的记忆工具。"""

    def __init__(self, store: MemoryStore):
        super().__init__(name="memory_tools")
        self.store = store
        self.register(self.save_memory)
        self.register(self.list_memories)
        self.register(self.delete_memory)

    def save_memory(self, category: str, content: str) -> str:
        """保存一条记忆到指定分类。分类如 preferences、lessons_learned、project_notes 等。

        Args:
            category: 记忆分类名称（如 preferences, lessons_learned）
            content: 要保存的记忆内容
        """
        self.store.save(category, content)
        return f"已保存记忆到分类 '{category}'。"

    def list_memories(self) -> str:
        """列出所有已保存的记忆分类及内容摘要。"""
        entries = self.store.list_entries()
        if not entries:
            return "当前没有保存任何记忆。"
        lines = []
        for cat, summary in entries.items():
            lines.append(f"- **{cat}**: {summary}")
        return "\n".join(lines)

    def delete_memory(self, category: str) -> str:
        """删除指定分类的记忆。

        Args:
            category: 要删除的记忆分类名称
        """
        if self.store.delete(category):
            return f"已删除记忆分类 '{category}'。"
        return f"未找到记忆分类 '{category}'。"
