"""CLI 入口：python -m hybot 或 hybot 命令。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

from hybot.config import (
    add_trusted_workspace,
    init_workspace,
    is_workspace_trusted,
    load_merged_config,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="HyBot AI CLI Agent")
    parser.add_argument("-c", "--config", default=None, help="配置文件路径（默认 ~/.hybot/config.yaml）")
    parser.add_argument("-s", "--session", default=None, help="会话 ID（用于恢复历史会话）")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    args = parser.parse_args()

    load_dotenv()

    cwd = Path.cwd()

    # 工作区信任检查
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

    from hybot.agent import build_and_run

    asyncio.run(build_and_run(config, session_id=args.session, workspace=cwd))


if __name__ == "__main__":
    main()
