"""结构化输出模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunSummary(BaseModel):
    """非交互模式的结构化输出。"""

    status: str = "success"  # "success" | "error" | "partial"
    summary: str = ""
    files_modified: list[str] = Field(default_factory=list)
    files_created: list[str] = Field(default_factory=list)
    commands_run: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
