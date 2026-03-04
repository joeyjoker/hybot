"""对话全文存档与检索。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ConversationLogger:
    """将完整对话保存为 JSON 文件，供后续检索使用。"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

    def save(self, session_id: str, messages: list) -> Path:
        """将完整对话保存为 JSON 文件。

        Args:
            session_id: 会话 ID。
            messages: agno Message 对象列表。

        Returns:
            保存的文件路径。
        """
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_id = session_id[:8] if session_id else "unknown"
        filename = f"{date_str}_{short_id}.json"
        filepath = self.log_dir / filename

        records: list[dict[str, Any]] = []
        for msg in messages:
            record: dict[str, Any] = {"role": getattr(msg, "role", "unknown")}
            content = getattr(msg, "content", None)
            if content is not None:
                record["content"] = content if isinstance(content, str) else str(content)
            tool_name = getattr(msg, "tool_name", None)
            if tool_name:
                record["tool_name"] = tool_name
            tool_call_id = getattr(msg, "tool_call_id", None)
            if tool_call_id:
                record["tool_call_id"] = tool_call_id
            created_at = getattr(msg, "created_at", None)
            if created_at:
                record["created_at"] = created_at
            records.append(record)

        data = {
            "session_id": session_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(records),
            "messages": records,
        }
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return filepath

    def list_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        """列出最近的对话记录。

        Returns:
            每条记录包含 filename, session_id, saved_at, message_count。
        """
        files = sorted(self.log_dir.glob("*.json"), reverse=True)
        results: list[dict[str, Any]] = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append({
                    "filename": f.name,
                    "session_id": data.get("session_id", ""),
                    "saved_at": data.get("saved_at", ""),
                    "message_count": data.get("message_count", 0),
                })
            except (json.JSONDecodeError, OSError):
                continue
        return results

    def load(self, filename: str) -> list[dict[str, Any]]:
        """加载指定对话的完整消息列表。"""
        filepath = self.log_dir / filename
        if not filepath.exists():
            return []
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return data.get("messages", [])
        except (json.JSONDecodeError, OSError):
            return []

    def search(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        """按关键词搜索历史对话内容。

        Returns:
            匹配的记录列表，包含 filename, session_id, matches（匹配的消息片段）。
        """
        keyword_lower = keyword.lower()
        results: list[dict[str, Any]] = []
        files = sorted(self.log_dir.glob("*.json"), reverse=True)
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            matches: list[str] = []
            for msg in data.get("messages", []):
                content = msg.get("content", "")
                if content and keyword_lower in content.lower():
                    # 截取匹配片段
                    idx = content.lower().index(keyword_lower)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(keyword) + 50)
                    snippet = content[start:end]
                    if start > 0:
                        snippet = "..." + snippet
                    if end < len(content):
                        snippet = snippet + "..."
                    matches.append(snippet)
            if matches:
                results.append({
                    "filename": f.name,
                    "session_id": data.get("session_id", ""),
                    "saved_at": data.get("saved_at", ""),
                    "matches": matches[:5],  # 每个文件最多显示 5 条匹配
                })
                if len(results) >= limit:
                    break
        return results
