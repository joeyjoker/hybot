import urllib.parse
import requests
from dataclasses import dataclass
from typing import Any, Dict, Optional


class FetchMarkdownError(Exception):
    """抓取网页 Markdown 失败。"""
    pass


@dataclass
class FetchMarkdownResult:
    url: str
    jina_url: str
    markdown: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "jina_url": self.jina_url,
            "markdown": self.markdown,
        }


class FetchMarkdownSkill:
    """通过 r.jina.ai 把任意网页转换为 Markdown 文本。

    原理：
    - 对原始 URL 进行 URL 编码
    - 访问 https://r.jina.ai/<encoded_url>
    - 读取返回的 Markdown 文本
    """

    def __init__(self, session: Optional[requests.Session] = None, base_url: str = "https://r.jina.ai"):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def fetch_markdown(self, url: str) -> Dict[str, Any]:
        """抓取指定网页，并返回其 Markdown 版本内容。

        :param url: 原始网页 URL，例如 "https://example.com/article"
        :return: 包含原始 URL、Jina 代理 URL、Markdown 文本的字典
        """
        if not url.startswith("http://") and not url.startswith("https://"):
            raise FetchMarkdownError("url 必须以 http:// 或 https:// 开头")

        encoded = urllib.parse.quote(url, safe="")
        jina_url = f"{self.base_url}/{encoded}"

        try:
            resp = self.session.get(jina_url, timeout=20)
        except requests.RequestException as e:
            raise FetchMarkdownError(f"请求 r.jina.ai 失败: {e}") from e

        if resp.status_code != 200:
            raise FetchMarkdownError(f"r.jina.ai 返回错误状态码 {resp.status_code}: {resp.text[:200]}")

        markdown = resp.text
        result = FetchMarkdownResult(url=url, jina_url=jina_url, markdown=markdown)
        return result.to_dict()