"""
乐意AI - 计算器工具

安全的数学表达式计算。
"""

import re
import math
from typing import Union

from .registry import register_tool


# 安全的内置函数白名单
SAFE_BUILTINS = {
    "abs": abs, "round": round, "max": max, "min": min,
    "sum": sum, "pow": pow,
}

# 安全的数学函数白名单
SAFE_MATH = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "pi": math.pi, "e": math.e,
    "floor": math.floor, "ceil": math.ceil, "factorial": math.factorial,
}


def _safe_eval(expression: str) -> Union[float, str]:
    """安全地计算数学表达式"""
    # 只允许数字、运算符、括号、空格、小数点
    if not re.match(r'^[\d\s+\-*/().,%^sqrt|sincostanlogexpPie]+$', expression):
        return "不支持的表达式，请使用基本的数学运算"

    try:
        # 替换 ^ 为 **
        expr = expression.replace("^", "**")

        # 创建安全环境
        safe_dict = {}
        safe_dict.update(SAFE_BUILTINS)
        safe_dict.update(SAFE_MATH)

        result = eval(expr, {"__builtins__": {}}, safe_dict)

        if isinstance(result, float):
            if result == int(result):
                return int(result)
            return round(result, 10)
        return result
    except ZeroDivisionError:
        return "除数不能为零"
    except Exception as e:
        return f"计算错误: {e}"


@register_tool(
    name="calculator",
    description="执行数学计算，支持加减乘除、幂运算、三角函数、对数等。当用户需要计算时使用此工具",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，例如: (15 + 3) * 2, sqrt(144), sin(30), 2^10",
            },
        },
        "required": ["expression"],
    },
)
def calculator(expression: str) -> str:
    """
    计算数学表达式

    Args:
        expression: 数学表达式

    Returns:
        计算结果
    """
    result = _safe_eval(expression)
    return f"{expression} = {result}"