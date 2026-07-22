"""
乐意AI - 联网搜索工具

使用 DuckDuckGo 免费搜索引擎（直接 HTTP 请求，无需第三方库）。
"""

import re
import urllib.parse
from typing import Optional, List

from .registry import register_tool


def _clean_url(url: str) -> str:
    """从 DuckDuckGo 跳转链接中提取真实 URL"""
    # 处理 //duckduckgo.com/l/?uddg=REAL_URL 格式
    if "uddg=" in url:
        import urllib.parse
        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "uddg" in parsed:
            return parsed["uddg"][0]
    # 如果是以 // 开头，补上 https:
    if url.startswith("//"):
        url = "https:" + url
    return url


def _search_duckduckgo(query: str, max_results: int = 5) -> str:
    """执行 DuckDuckGo 搜索（直接 HTTP 请求）"""
    results = []

    try:
        # 方法1: 使用 DuckDuckGo HTML 搜索
        results = _search_via_html(query, max_results)
    except Exception:
        pass

    if not results:
        try:
            # 方法2: 使用 DuckDuckGo Lite 搜索
            results = _search_via_lite(query, max_results)
        except Exception:
            pass

    if not results:
        return f"搜索失败，无法获取 '{query}' 的结果。请检查网络连接后重试。"

    output = []
    for i, r in enumerate(results[:max_results], 1):
        title = r.get("title", "无标题")
        body = r.get("body", "")
        href = _clean_url(r.get("href", ""))
        # 清理过长的文本
        if len(body) > 200:
            body = body[:200] + "..."
        output.append(f"{i}. {title}\n   {body}\n   来源: {href}")

    return "\n\n".join(output)


def _search_via_html(query: str, max_results: int = 5) -> List[dict]:
    """通过HTML搜索页面获取结果"""
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()

    results = []
    # 解析 HTML 结果
    # 查找结果区块: <a class="result__a" ...>
    for match in re.finditer(
        r'<a[^>]*class="result__a"[^>]*href="(.*?)"[^>]*>(.*?)</a>',
        r.text,
        re.DOTALL,
    ):
        href = match.group(1)
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()

        # 查找对应的摘要
        snippet = ""
        snippet_match = re.search(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            r.text[match.end():match.end() + 1000],
            re.DOTALL,
        )
        if snippet_match:
            snippet = re.sub(r"<[^>]+>", "", snippet_match.group(1)).strip()

        results.append({"title": title, "body": snippet, "href": href})
        if len(results) >= max_results:
            break

    return results


def _search_via_lite(query: str, max_results: int = 5) -> List[dict]:
    """通过DuckDuckGo Lite版本搜索"""
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    r = requests.post(
        "https://lite.duckduckgo.com/lite/",
        data={"q": query},
        headers=headers,
        timeout=15,
    )
    r.raise_for_status()

    results = []
    # 解析 Lite 版结果
    rows = re.findall(
        r'<tr>\s*<td[^>]*>\s*<a[^>]*href="(.*?)"[^>]*>(.*?)</a>',
        r.text,
        re.DOTALL,
    )
    for href, title_html in rows[:max_results]:
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        results.append({"title": title, "body": "", "href": href})

    return results


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