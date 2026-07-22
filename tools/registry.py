"""
乐意AI - 工具注册框架

管理所有工具的注册、查找和执行。
Function Calling 集成。
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    parameters: Dict  # JSON Schema 格式
    handler: Callable  # 执行函数

    def to_openai_tool(self) -> Dict:
        """转换为 OpenAI Function Calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """列出所有工具"""
        return list(self._tools.values())

    def get_openai_tools(self) -> List[Dict]:
        """获取所有工具的 OpenAI Function Calling 格式"""
        return [t.to_openai_tool() for t in self._tools.values()]

    def execute(self, name: str, arguments: Dict) -> str:
        """
        执行工具

        Args:
            name: 工具名称
            arguments: 参数字典

        Returns:
            工具执行结果（字符串形式）
        """
        tool = self.get(name)
        if not tool:
            return f"错误: 未知工具 '{name}'"
        try:
            result = tool.handler(**arguments)
            return str(result)
        except Exception as e:
            return f"工具执行错误: {e}"

    def has_tools(self) -> bool:
        """是否已注册工具"""
        return len(self._tools) > 0


# 全局工具注册中心
global_registry = ToolRegistry()


def register_tool(name: str, description: str, parameters: Dict):
    """装饰器：注册工具"""
    def decorator(handler: Callable):
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )
        global_registry.register(tool)
        return handler
    return decorator


def parse_tool_call(response) -> Optional[Tuple[str, Dict]]:
    """
    解析API响应中的工具调用

    Args:
        response: OpenAI API响应对象

    Returns:
        (工具名称, 参数字典) 或 None
    """
    try:
        msg = response.choices[0].message
        if msg.tool_calls:
            for call in msg.tool_calls:
                import json
                name = call.function.name
                arguments = json.loads(call.function.arguments)
                return name, arguments
    except (AttributeError, IndexError, json.JSONDecodeError):
        pass
    return None