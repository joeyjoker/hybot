# Fetch Markdown Skill

通过 [r.jina.ai](https://r.jina.ai) 把任意网页转换为 **Markdown 文本** 的 Agent Skill。

## 能力描述（Functions）

### `fetch_markdown`

抓取指定网页，并返回其 Markdown 版本内容。

- **脚本入口（如何调用）**

  - 模块（module）: `skills.fetch_markdown.scripts.fetch_markdown`
  - 函数（function）: `run(params: dict) -> dict`

  约定：
  - Agent 或调用方以一个 `dict` 作为参数调用 `run`
  - `params` 中必须包含键 `"url"`
  - `run` 返回一个 `dict`，结构如下：

  ```json
  {
    "ok": true,
    "data": { "...": "成功时的结果" },
    "error": null
  }
  ```

- **入参（JSON Schema）**

```json
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "原始网页 URL，例如 'https://example.com/article'",
      "minLength": 1
    }
  },
  "required": ["url"]
}
```

- **出参（结构说明）**

```json
{
  "url": "string, 原始网页 URL",
  "jina_url": "string, 实际访问的 r.jina.ai 代理 URL",
  "markdown": "string, 该网页对应的 Markdown 文本内容"
}
```

## 使用方式

### 1. 作为 Agent 的工具调用（示意）

当用户说：

> 帮我把这篇文章转成 Markdown：https://example.com/article

Agent 可以选择调用工具：

- tool name: `fetch_markdown`
- arguments:

```json
{
  "url": "https://example.com/article"
}
```

返回：

```json
{
  "url": "https://example.com/article",
  "jina_url": "https://r.jina.ai/https%3A%2F%2Fexample.com%2Farticle",
  "markdown": "# 文章标题...\n..."
}
```

然后 Agent 可以继续对 `markdown` 字段做摘要、问答、重写等操作。

### 2. 在 Python 代码中直接调用

```python
from skills.fetch_markdown import FetchMarkdownSkill

skill = FetchMarkdownSkill()
result = skill.fetch_markdown("https://example.com/article")
print(result["markdown"])
```

## 实现细节

- 对原始 URL 使用 `urllib.parse.quote(url, safe="")` 做 URL 编码
- 拼接访问地址：`https://r.jina.ai/<encoded_url>`
- 使用 HTTP GET 获取返回内容（Markdown 文本）
- 错误处理：
  - 入参不是以 `http://` 或 `https://` 开头 → 抛 `FetchMarkdownError`
  - 请求失败或状态码非 200 → 抛 `FetchMarkdownError`