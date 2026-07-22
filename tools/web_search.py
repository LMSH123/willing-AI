"""
乐意AI - 联网搜索工具

使用 DuckDuckGo 免费搜索引擎。
"""

from typing import Optional, List

from .registry import register_tool


def _search_duckduckgo(query: str, max_results: int = 5) -> str:
    """执行 DuckDuckGo 搜索"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
    except ImportError:
        return "搜索功能不可用：请安装 duckduckgo_search 包 (pip install duckduckgo_search)"
    except Exception as e:
        return f"搜索失败: {e}"

    if not results:
        return f"未找到 '{query}' 的相关结果。"

    output = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "无标题")
        body = r.get("body", "")
        href = r.get("href", "")
        output.append(f"{i}. {title}\n   {body}\n   来源: {href}")

    return "\n\n".join(output)


@register_tool(
    name="web_search",
    description="搜索互联网获取最新信息，当需要了解实时新闻、最新动态或不确定的事实时应使用此工具",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，应简洁明确",
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量 (1-10)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)
def web_search(query: str, max_results: int = 5) -> str:
    """
    搜索互联网

    Args:
        query: 搜索关键词
        max_results: 返回结果数量

    Returns:
        搜索结果文本
    """
    return _search_duckduckgo(query, min(max_results, 10))