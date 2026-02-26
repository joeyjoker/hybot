"""项目结构感知：通过文件探测自动识别项目信息。"""

from __future__ import annotations

import subprocess
from pathlib import Path

# 项目标识文件 -> (语言, 包管理器/框架 提示)
SIGNATURES: list[tuple[str, str, str]] = [
    # (文件名, 语言, 包管理器/框架)
    ("pyproject.toml", "Python", "pyproject.toml"),
    ("setup.py", "Python", "setup.py"),
    ("setup.cfg", "Python", "setup.cfg"),
    ("requirements.txt", "Python", "pip"),
    ("Pipfile", "Python", "pipenv"),
    ("poetry.lock", "Python", "poetry"),
    ("uv.lock", "Python", "uv"),
    ("package.json", "JavaScript/TypeScript", "npm/yarn"),
    ("yarn.lock", "JavaScript/TypeScript", "yarn"),
    ("pnpm-lock.yaml", "JavaScript/TypeScript", "pnpm"),
    ("bun.lockb", "JavaScript/TypeScript", "bun"),
    ("tsconfig.json", "TypeScript", "tsc"),
    ("Cargo.toml", "Rust", "cargo"),
    ("go.mod", "Go", "go modules"),
    ("pom.xml", "Java", "maven"),
    ("build.gradle", "Java/Kotlin", "gradle"),
    ("build.gradle.kts", "Kotlin", "gradle-kts"),
    ("Gemfile", "Ruby", "bundler"),
    ("composer.json", "PHP", "composer"),
    ("CMakeLists.txt", "C/C++", "cmake"),
    ("Makefile", "C/C++", "make"),
    ("*.csproj", "C#", ".NET"),
    ("*.sln", "C#", ".NET"),
    ("pubspec.yaml", "Dart", "pub"),
    ("mix.exs", "Elixir", "mix"),
    ("Dockerfile", "-", "docker"),
    ("docker-compose.yml", "-", "docker-compose"),
    ("docker-compose.yaml", "-", "docker-compose"),
]

FRAMEWORK_HINTS: dict[str, list[tuple[str, str]]] = {
    "Python": [
        ("manage.py", "Django"),
        ("app.py", "Flask (可能)"),
        ("main.py", "FastAPI/通用入口"),
        ("conftest.py", "pytest"),
    ],
    "JavaScript/TypeScript": [
        ("next.config.js", "Next.js"),
        ("next.config.mjs", "Next.js"),
        ("nuxt.config.ts", "Nuxt"),
        ("angular.json", "Angular"),
        ("vite.config.ts", "Vite"),
        ("webpack.config.js", "Webpack"),
    ],
}


def _detect_git_remote(workspace: Path) -> str | None:
    """尝试获取 git remote URL。"""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _detect_git_branch(workspace: Path) -> str | None:
    """尝试获取当前 git 分支名。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def scan_project(workspace: Path) -> str:
    """扫描项目目录，返回项目信息的 Markdown 文本。"""
    lines: list[str] = []
    lines.append(f"**项目路径**: `{workspace}`")

    # Git 信息
    git_remote = _detect_git_remote(workspace)
    git_branch = _detect_git_branch(workspace)
    if git_remote:
        lines.append(f"**Git Remote**: `{git_remote}`")
    if git_branch:
        lines.append(f"**Git Branch**: `{git_branch}`")

    # 语言和工具检测
    languages: set[str] = set()
    tools_found: list[str] = []
    for sig_file, lang, tool in SIGNATURES:
        if "*" in sig_file:
            matches = list(workspace.glob(sig_file))
            if matches:
                if lang != "-":
                    languages.add(lang)
                tools_found.append(tool)
        elif (workspace / sig_file).exists():
            if lang != "-":
                languages.add(lang)
            tools_found.append(tool)

    if languages:
        lines.append(f"**语言**: {', '.join(sorted(languages))}")
    if tools_found:
        lines.append(f"**工具/包管理器**: {', '.join(dict.fromkeys(tools_found))}")

    # 框架检测
    frameworks: list[str] = []
    for lang in languages:
        hints = FRAMEWORK_HINTS.get(lang, [])
        for hint_file, framework in hints:
            if (workspace / hint_file).exists():
                frameworks.append(framework)
    if frameworks:
        lines.append(f"**框架**: {', '.join(frameworks)}")

    # 常见目录结构
    notable_dirs = ["src", "lib", "app", "tests", "test", "docs", "scripts", "config"]
    found_dirs = [d for d in notable_dirs if (workspace / d).is_dir()]
    if found_dirs:
        lines.append(f"**目录结构**: {', '.join(f'`{d}/`' for d in found_dirs)}")

    # 入口文件检测
    entry_files = ["main.py", "app.py", "index.ts", "index.js", "main.go", "main.rs"]
    found_entries = []
    for ef in entry_files:
        if (workspace / ef).exists():
            found_entries.append(ef)
        elif (workspace / "src" / ef).exists():
            found_entries.append(f"src/{ef}")
    if found_entries:
        lines.append(f"**入口文件**: {', '.join(f'`{e}`' for e in found_entries)}")

    return "\n".join(lines) if lines else "未检测到已知项目结构。"


def load_or_scan(workspace: Path, cache: bool = True) -> str:
    """加载缓存的项目信息，或执行扫描并缓存。"""
    cache_path = workspace / ".hybot" / "project_info.md"

    if cache and cache_path.exists():
        return cache_path.read_text(encoding="utf-8").strip()

    info = scan_project(workspace)

    if cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(info, encoding="utf-8")

    return info
