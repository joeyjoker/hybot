"""Sub-agent 支持：从 .hybot/agents/*.yaml 加载子 Agent 定义。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import yaml
from agno.agent import Agent
from agno.tools import Toolkit
from pydantic import BaseModel, Field


class SubAgentConfig(BaseModel):
    """Sub-agent YAML 配置模型。"""

    name: str
    description: str = ""
    model: dict = Field(default_factory=lambda: {"provider": "openai", "id": "gpt-4o"})
    instructions: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)  # "coding", "python", "git" 等


def load_subagent_configs(workspace: Path) -> list[SubAgentConfig]:
    """从 .hybot/agents/*.yaml 加载所有 sub-agent 配置。"""
    agents_dir = workspace / ".hybot" / "agents"
    if not agents_dir.is_dir():
        return []
    configs: list[SubAgentConfig] = []
    for yaml_file in sorted(agents_dir.glob("*.yaml")):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data:
                configs.append(SubAgentConfig(**data))
        except Exception:
            continue
    return configs


def _build_subagent_model(model_config: dict) -> Any:
    """根据 sub-agent 的 model 配置构建 Model 实例。"""
    provider = model_config.get("provider", "openai")
    model_id = model_config.get("id", "gpt-4o")
    common: dict = {"id": model_id}

    api_key = model_config.get("api_key")
    if api_key:
        common["api_key"] = api_key

    if provider == "openai":
        from agno.models.openai import OpenAIChat
        base_url = model_config.get("base_url")
        return OpenAIChat(**common, base_url=base_url)

    if provider == "openai_responses":
        from agno.models.openai import OpenAIResponses
        base_url = model_config.get("base_url")
        return OpenAIResponses(**common, base_url=base_url)

    if provider == "anthropic":
        from agno.models.anthropic import Claude
        return Claude(**common)

    if provider == "gemini":
        from agno.models.google import Gemini
        return Gemini(**common)

    # 回退到 OpenAI
    from agno.models.openai import OpenAIChat
    return OpenAIChat(**common)


def _build_subagent_tools(tool_names: list[str], workspace: Path) -> list:
    """根据工具名称列表构建工具实例。"""
    tools: list = []
    for name in tool_names:
        if name == "coding":
            from agno.tools.coding import CodingTools
            tools.append(CodingTools(base_dir=str(workspace)))
        elif name == "python":
            from agno.tools.python import PythonTools
            tools.append(PythonTools())
        elif name == "git":
            from hybot.tools.git_tools import GitTools
            tools.append(GitTools(base_dir=str(workspace)))
    return tools


class SubAgentTools(Toolkit):
    """为每个 sub-agent 动态创建工具方法，主 Agent 可通过工具调用委派任务。

    Sub-agent 懒加载，首次调用时才构建。
    """

    def __init__(self, configs: list[SubAgentConfig], workspace: Path):
        super().__init__(name="subagent_tools")
        self.configs = {c.name: c for c in configs}
        self.workspace = workspace
        self._agents: dict[str, Agent] = {}

        # 为每个 sub-agent 动态注册一个调用工具
        for cfg in configs:
            self._register_subagent_tool(cfg)

    def _register_subagent_tool(self, cfg: SubAgentConfig) -> None:
        """为单个 sub-agent 创建并注册工具方法。"""
        agent_name = cfg.name

        async def invoke(task: str) -> str:
            f"""调用 {agent_name} sub-agent 执行任务。{cfg.description}

            Args:
                task: 要委派给 {agent_name} 的任务描述
            """
            agent = self._get_or_create_agent(agent_name)
            response = await agent.arun(task)
            return response.content if response else "Sub-agent 未返回结果。"

        # 设置函数名和文档字符串以便 Agent 发现
        invoke.__name__ = f"invoke_{agent_name}"
        invoke.__doc__ = (
            f"调用 {agent_name} sub-agent 执行任务。{cfg.description}\n\n"
            f"Args:\n    task: 要委派给 {agent_name} 的任务描述"
        )
        self.register(invoke)

    def _get_or_create_agent(self, name: str) -> Agent:
        """懒加载 sub-agent。"""
        if name in self._agents:
            return self._agents[name]

        cfg = self.configs[name]
        model = _build_subagent_model(cfg.model)
        tools = _build_subagent_tools(cfg.tools, self.workspace)

        agent = Agent(
            model=model,
            name=cfg.name,
            description=cfg.description,
            instructions=cfg.instructions,
            tools=tools,
            markdown=True,
        )
        self._agents[name] = agent
        return agent
