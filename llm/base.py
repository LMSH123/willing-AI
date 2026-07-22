"""
乐意AI - LLM客户端抽象基类

定义所有大模型客户端必须实现的接口。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Generator, Any, Tuple


class BaseLLMClient(ABC):
    """LLM客户端抽象基类"""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> str:
        """
        发送对话请求，返回完整回复

        Args:
            messages: 消息列表 [{"role": "user", "content": "你好"}]
            tools: 工具定义列表（Function Calling用）
            **kwargs: 其他参数（temperature, max_tokens等）

        Returns:
            模型回复文本
        """
        ...

    @abstractmethod
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        """
        发送流式对话请求，逐块生成回复

        Args:
            messages: 消息列表
            tools: 工具定义列表
            **kwargs: 其他参数

        Yields:
            回复文本片段
        """
        ...

    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tool_registry: Any,
        max_tool_rounds: int = 5,
        **kwargs: Any,
    ) -> Tuple[str, List[Dict]]:
        """
        带工具调用的对话（自动处理Function Calling循环）

        Args:
            messages: 消息列表
            tool_registry: 工具注册中心 (ToolRegistry)
            max_tool_rounds: 最大工具调用轮数
            **kwargs: 其他参数

        Returns:
            (最终回复文本, 完整消息列表)
        """
        tools = tool_registry.get_openai_tools() if tool_registry.has_tools() else None
        current_messages = list(messages)

        for _ in range(max_tool_rounds):
            response = self._raw_chat(current_messages, tools=tools, **kwargs)

            # 检查是否有工具调用
            tool_call = self._parse_tool_call(response)
            if not tool_call:
                # 没有工具调用，直接返回文本回复
                text = self._extract_text(response)
                current_messages.append({"role": "assistant", "content": text})
                return text, current_messages

            # 有工具调用 - 执行工具
            name, arguments = tool_call

            # 添加助手消息（包含工具调用信息）
            current_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": self._get_tool_call_id(response),
                    "type": "function",
                    "function": {"name": name, "arguments": str(arguments)},
                }],
            })

            # 执行工具
            result = tool_registry.execute(name, arguments)

            # 添加工具执行结果
            current_messages.append({
                "role": "tool",
                "tool_call_id": self._get_tool_call_id(response),
                "content": result,
            })

        # 超过最大轮数，返回最后一条消息
        return "抱歉，工具调用次数过多，请简化你的请求。", current_messages

    def stream_chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tool_registry: Any,
        max_tool_rounds: int = 5,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        """
        带工具调用的流式对话

        先检测是否需要工具调用（非流式），然后流式输出最终回复。
        """
        tools = tool_registry.get_openai_tools() if tool_registry.has_tools() else None
        current_messages = list(messages)

        for _ in range(max_tool_rounds):
            response = self._raw_chat(current_messages, tools=tools, **kwargs)

            tool_call = self._parse_tool_call(response)
            if not tool_call:
                # 没有工具调用，直接流式输出
                text = self._extract_text(response)
                current_messages.append({"role": "assistant", "content": text})
                yield text
                return

            # 有工具调用 - 执行
            name, arguments = tool_call
            yield f"[使用工具: {name}]"

            current_messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": self._get_tool_call_id(response),
                    "type": "function",
                    "function": {"name": name, "arguments": str(arguments)},
                }],
            })

            result = tool_registry.execute(name, arguments)
            current_messages.append({
                "role": "tool",
                "tool_call_id": self._get_tool_call_id(response),
                "content": result,
            })

    @abstractmethod
    def _raw_chat(self, messages: List[Dict], **kwargs) -> Any:
        """
        原始API调用（返回完整响应对象，用于解析工具调用）
        """
        ...

    @abstractmethod
    def _parse_tool_call(self, response: Any) -> Optional[Tuple[str, Dict]]:
        """
        解析响应中的工具调用
        返回 (工具名称, 参数字典) 或 None
        """
        ...

    @abstractmethod
    def _extract_text(self, response: Any) -> str:
        """从响应中提取文本"""
        ...

    @abstractmethod
    def _get_tool_call_id(self, response: Any) -> str:
        """获取工具调用ID"""
        ...

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        ...

    def count_tokens(self, text: str) -> int:
        """
        估算文本的token数量（简易实现，子类可覆盖）

        Args:
            text: 输入文本

        Returns:
            估算的token数
        """
        # 中文约1.5字符/token，英文约4字符/token
        # 简单按2字符/token估算
        return max(1, len(text) // 2)

    @property
    @abstractmethod
    def model_name(self) -> str:
        """当前使用的模型名称"""
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """后端名称（如 deepseek / openai）"""
        ...