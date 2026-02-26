"""YAML 配置加载与 Pydantic 验证。"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

# 全局配置目录
HYBOT_HOME = Path("~/.hybot").expanduser()

# 项目本地目录名
LOCAL_DIR_NAME = ".hybot"

# workspaces.yaml 路径
WORKSPACES_FILE = HYBOT_HOME / "workspaces.yaml"

# 本地 config.yaml 模板内容
LOCAL_CONFIG_TEMPLATE = """\
# 项目本地配置（覆盖全局 ~/.hybot/config.yaml）
# 只需填写需要覆盖的字段，其余继承全局配置
"""

# AGENT.md 模板内容
AGENT_MD_TEMPLATE = """\
# AGENT.md

<!-- 在此编写项目级 agent 指令，启动时自动加载 -->
"""


class ModelConfig(BaseModel):
    provider: str = "openai"  # "openai" | "openai_responses" | "anthropic" | "gemini"
    id: str = "gpt-4o"
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    reasoning_effort: Optional[str] = None  # "minimal" | "low" | "medium" | "high"
    reasoning_summary: Optional[str] = None  # "auto" | "concise" | "detailed" (仅 openai_responses)


class AgentConfig(BaseModel):
    name: str = "HyBot"
    description: str = "AI 编码助手，可执行文件操作、Shell 命令、运行 Python 代码"
    instructions: list[str] = Field(default_factory=lambda: [
        "你是一个强大的 AI 编码助手。",
        "使用中文回复用户。",
        "在修改文件前先阅读文件内容。",
    ])
    markdown: bool = True
    stream: bool = True
    reasoning: bool = False
    show_reasoning: bool = True
    add_history_to_context: bool = True
    num_history_runs: int = 10
    add_datetime_to_context: bool = True


class CodingToolsConfig(BaseModel):
    enabled: bool = True
    base_dir: str = "."
    all: bool = True


class PythonToolsConfig(BaseModel):
    enabled: bool = True


class GitToolsConfig(BaseModel):
    enabled: bool = True


class WebToolsConfig(BaseModel):
    enabled: bool = False  # 默认关闭，避免意外联网
    enable_search: bool = True
    enable_fetch: bool = True


class ToolsConfig(BaseModel):
    coding: CodingToolsConfig = Field(default_factory=CodingToolsConfig)
    python: PythonToolsConfig = Field(default_factory=PythonToolsConfig)
    git: GitToolsConfig = Field(default_factory=GitToolsConfig)
    web: WebToolsConfig = Field(default_factory=WebToolsConfig)


class MemoryConfig(BaseModel):
    enabled: bool = True
    path: str = "~/.hybot/memory"


class ApprovalConfig(BaseModel):
    mode: str = "dangerous"  # "always" | "dangerous" | "never"


class ProjectConfig(BaseModel):
    scan_on_startup: bool = True
    cache_scan: bool = True


class StorageConfig(BaseModel):
    type: str = "sqlite"
    db_file: str = "~/.hybot/sessions.db"


class SkillsConfig(BaseModel):
    path: Optional[str] = str(HYBOT_HOME / "skills")


class MCPServerConfig(BaseModel):
    name: str
    command: Optional[str] = None
    url: Optional[str] = None
    transport: Optional[str] = None
    env: Optional[dict[str, str]] = None


class AppConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)


def default_config_path() -> Path:
    """返回默认配置文件路径：~/.hybot/config.yaml"""
    return HYBOT_HOME / "config.yaml"


# ---------------------------------------------------------------------------
# workspaces.yaml 管理
# ---------------------------------------------------------------------------

def _normalize_path(path: str) -> str:
    """将路径统一为 resolved 的 POSIX 字符串，便于比较。"""
    return Path(path).resolve().as_posix()


def load_trusted_workspaces() -> list[str]:
    """读取 ~/.hybot/workspaces.yaml，返回已信任的工作区路径列表。"""
    if not WORKSPACES_FILE.exists():
        return []
    with open(WORKSPACES_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("trusted", [])


def add_trusted_workspace(path: str) -> None:
    """追加路径到 workspaces.yaml 的 trusted 列表。"""
    workspaces = load_trusted_workspaces()
    normalized = _normalize_path(path)
    if normalized not in [_normalize_path(w) for w in workspaces]:
        workspaces.append(normalized)
    WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WORKSPACES_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump({"trusted": workspaces}, f, allow_unicode=True)


def is_workspace_trusted(path: str) -> bool:
    """检查路径是否已在 trusted 列表中。"""
    normalized = _normalize_path(path)
    return normalized in [_normalize_path(w) for w in load_trusted_workspaces()]


# ---------------------------------------------------------------------------
# 工作区初始化
# ---------------------------------------------------------------------------

def init_workspace(workspace: Path) -> None:
    """创建 .hybot/ 目录，并生成空的 config.yaml 模板和 AGENT.md 模板。"""
    local_dir = workspace / LOCAL_DIR_NAME
    local_dir.mkdir(parents=True, exist_ok=True)
    local_config = local_dir / "config.yaml"
    if not local_config.exists():
        local_config.write_text(LOCAL_CONFIG_TEMPLATE, encoding="utf-8")
    agent_md = workspace / "AGENT.md"
    if not agent_md.exists():
        agent_md.write_text(AGENT_MD_TEMPLATE, encoding="utf-8")


def load_agent_md(workspace: Path) -> list[str]:
    """按层级读取 AGENT.md 文件，返回内容列表。"""
    candidates = [
        HYBOT_HOME / "AGENT.md",                  # 全局
        workspace / "AGENT.md",                   # 项目根
        workspace / LOCAL_DIR_NAME / "AGENT.md",  # 本地
    ]
    contents = []
    for path in candidates:
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                contents.append(text)
    return contents


# ---------------------------------------------------------------------------
# 配置合并
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """递归深度合并两个 dict。

    - dict 类型递归合并（override 的 key 覆盖 base 同名 key）
    - list / 标量类型：override 完全替换 base
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_yaml(path: Path) -> dict:
    """安全读取 YAML 文件，不存在或为空时返回空 dict。"""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_merged_config(
    workspace: Path,
    global_config_path: Path | None = None,
) -> AppConfig:
    """加载并合并全局 + 本地配置，返回 AppConfig。

    1. 加载全局 ~/.hybot/config.yaml 作为 base
    2. 加载本地 <workspace>/.hybot/config.yaml，deep merge 覆盖 base
    3. 强制将 storage.db_file 指向 <workspace>/.hybot/sessions.db
    4. tools.coding.base_dir 默认指向 workspace 目录
    """
    global_path = global_config_path or default_config_path()
    base = _load_yaml(global_path)

    local_path = workspace / LOCAL_DIR_NAME / "config.yaml"
    local = _load_yaml(local_path)

    merged = _deep_merge(base, local) if local else base

    # 强制设置本地路径
    merged.setdefault("storage", {})
    merged["storage"]["db_file"] = str(workspace / LOCAL_DIR_NAME / "sessions.db")

    merged.setdefault("tools", {}).setdefault("coding", {})
    if merged["tools"]["coding"].get("base_dir", ".") == ".":
        merged["tools"]["coding"]["base_dir"] = str(workspace)

    return AppConfig(**merged)


# 保留旧接口作为 fallback（不走工作区合并逻辑）
def load_config(path: str | None = None) -> AppConfig:
    """读取 YAML 配置文件并返回 AppConfig 实例。

    如果未指定路径，使用 ~/.hybot/config.yaml。
    如果文件不存在则使用默认配置。
    """
    config_path = Path(path) if path else default_config_path()
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()
