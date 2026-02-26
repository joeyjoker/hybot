"""CLI 入口：python -m hybot 或 hybot 命令。"""

from __future__ import annotations

import argparse
import asyncio
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

from hybot.config import (
    add_trusted_workspace,
    init_workspace,
    is_workspace_trusted,
    load_merged_config,
)


def _run_async(coro) -> None:
    """运行异步协程，确保优雅关闭并抑制 Windows ProactorEventLoop 的资源警告。"""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(coro)
    except KeyboardInterrupt:
        pass
    finally:
        # 取消所有剩余任务
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        # 关闭所有异步生成器和事件循环
        loop.run_until_complete(loop.shutdown_asyncgens())
        # Python 3.11+ 提供 shutdown_default_executor
        if hasattr(loop, "shutdown_default_executor"):
            loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


def main() -> None:
    # 抑制 asyncio transport 关闭时的 ResourceWarning（Windows ProactorEventLoop 常见）
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed transport")
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed <socket")

    parser = argparse.ArgumentParser(description="HyBot AI CLI Agent")
    parser.add_argument("-c", "--config", default=None, help="配置文件路径（默认 ~/.hybot/config.yaml）")
    parser.add_argument("-s", "--session", default=None, help="会话 ID（用于恢复历史会话）")
    parser.add_argument("-r", "--run", default=None, help="非交互执行单个任务后退出")
    parser.add_argument("-p", "--project", default=None, help="指定工作目录（默认 cwd）")
    parser.add_argument("--output", default="text", choices=["text", "json"], help="输出格式：text（默认）| json")
    parser.add_argument("--no-stream", action="store_true", help="禁用流式输出")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()

    load_dotenv()

    cwd = Path(args.project).resolve() if args.project else Path.cwd()

    # --run 模式下自动信任工作区
    if args.run:
        if not is_workspace_trusted(str(cwd)):
            add_trusted_workspace(str(cwd))
            init_workspace(cwd)
    else:
        # 交互模式：工作区信任检查
        if not is_workspace_trusted(str(cwd)):
            answer = input(f"是否允许 hybot 在此目录运行？({cwd}) [y/N] ").strip().lower()
            if answer != "y":
                print("已取消。")
                sys.exit(0)
            add_trusted_workspace(str(cwd))
            init_workspace(cwd)

    # 加载合并配置（全局 + 本地）
    global_config_path = Path(args.config) if args.config else None
    config = load_merged_config(workspace=cwd, global_config_path=global_config_path)

    # --no-stream 覆盖配置
    if args.no_stream:
        config.agent.stream = False

    if args.run:
        from hybot.agent import build_and_run_once

        exit_code = asyncio.run(
            build_and_run_once(
                config,
                task=args.run,
                workspace=cwd,
                output_format=args.output,
            )
        )
        sys.exit(exit_code)
    else:
        from hybot.agent import build_and_run

        _run_async(build_and_run(config, session_id=args.session, workspace=cwd))


if __name__ == "__main__":
    main()
