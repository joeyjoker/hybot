from typing import Any, Dict

from skills.fetch_markdown.src.fetch_markdown_impl import (
    FetchMarkdownSkill,
    FetchMarkdownError,
)


def run(params: Dict[str, Any]) -> Dict[str, Any]:
    """Skill 入口函数。

    约定：
    - 输入: params 为一个 dict，必须包含键 "url"
    - 输出: 返回 dict:
      {
        "ok": bool,
        "data": { ...成功时的结果... } 或 None,
        "error": "错误信息字符串" 或 None
      }
    """
    url = params.get("url")
    if not isinstance(url, str) or not url:
        return {
            "ok": False,
            "data": None,
            "error": "参数 url 必须为非空字符串，例如 'https://example.com'",
        }

    skill = FetchMarkdownSkill()
    try:
        data = skill.fetch_markdown(url)
        return {
            "ok": True,
            "data": data,
            "error": None,
        }
    except FetchMarkdownError as e:
        return {
            "ok": False,
            "data": None,
            "error": f"抓取失败: {e}",
        }