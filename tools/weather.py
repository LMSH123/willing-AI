"""
乐意AI - 天气查询工具

使用 wttr.in 免费API获取天气信息。
"""

from typing import Optional

from .registry import register_tool


def _get_weather(city: str) -> str:
    """查询天气"""
    try:
        import httpx
        # 使用 wttr.in 的 JSON 格式
        url = f"https://wttr.in/{city}?format=j1&lang=zh"
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except ImportError:
        return "天气功能不可用：请安装 httpx 包 (pip install httpx)"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"未找到城市 '{city}' 的天气信息"
        return f"天气查询失败: {e}"
    except Exception as e:
        return f"天气查询失败: {e}"

    try:
        current = data["current_condition"][0]
        temp = current["temp_C"]
        feels_like = current["FeelsLikeC"]
        humidity = current["humidity"]
        desc = current["lang_zh"][0]["value"] if "lang_zh" in current else current["weatherDesc"][0]["value"]
        wind = current["windspeedKmph"]
        region = data["nearest_area"][0]["region"][0]["value"]
        country = data["nearest_area"][0]["country"][0]["value"]

        result = (
            f"📍 {city}, {region}, {country}\n"
            f"🌡️ 温度: {temp}°C (体感 {feels_like}°C)\n"
            f"☁️ 天气: {desc}\n"
            f"💧 湿度: {humidity}%\n"
            f"💨 风速: {wind} km/h"
        )
        return result
    except (KeyError, IndexError) as e:
        return f"解析天气数据失败: {e}"


@register_tool(
    name="weather",
    description="查询指定城市的实时天气信息，包括温度、湿度、风速等",
    parameters={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称，支持中文和英文，例如: 北京、上海、London",
            },
        },
        "required": ["city"],
    },
)
def weather(city: str) -> str:
    """
    查询天气

    Args:
        city: 城市名称

    Returns:
        天气信息
    """
    return _get_weather(city)