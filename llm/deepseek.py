"""
乐意AI - DeepSeek API 客户端

使用 OpenAI SDK 调用 DeepSeek API（兼容格式）。
"""

import json
from typing import List, Dict, Optional, Generator, Any, Tuple
from openai import OpenAI

from .base import BaseLLMClient


class DeepSeekClient(BaseLLMClient):
    """DeepSeek API 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        **kwargs: Any,
    ):
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._top_p = top_p
        self._extra_kwargs = kwargs

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def backend_name(self) -> str:
        return "deepseek"

    def _build_params(self, **kwargs: Any) -> dict:
        params = {
            "model": kwargs.pop("model", self._model),
            "temperature": kwargs.pop("temperature", self._temperature),
            "max_tokens": kwargs.pop("max_tokens", self._max_tokens),
            "top_p": kwargs.pop("top_p", self._top_p),
        }
        params.update(self._extra_kwargs)
        params.update(kwargs)
        return params

    def chat(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> str:
        params = self._build_params(**kwargs)
        params["messages"] = messages
        params["stream"] = False
        if tools:
            params["tools"] = tools
        response = self.client.chat.completions.create(**params)
        return response.choices[0].message.content or ""

    def stream_chat(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        **kwargs: Any,
    ) -> Generator[str, None, None]:
        params = self._build_params(**kwargs)
        params["messages"] = messages
        params["stream"] = True
        if tools:
            params["tools"] = tools
        response = self.client.chat.completions.create(**params)
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _raw_chat(self, messages: List[Dict], **kwargs) -> Any:
        """原始API调用，返回完整响应对象"""
        params = self._build_params(**kwargs)
        params["messages"] = messages
        params["stream"] = False
        if "tools" in kwargs:
            params["tools"] = kwargs["tools"]
        return self.client.chat.completions.create(**params)

    def _parse_tool_call(self, response: Any) -> Optional[Tuple[str, Dict]]:
        """解析工具调用"""
        try:
            msg = response.choices[0].message
            if msg.tool_calls:
                for call in msg.tool_calls:
                    name = call.function.name
                    arguments = json.loads(call.function.arguments)
                    return name, arguments
        except (AttributeError, IndexError, json.JSONDecodeError):
            pass
        return None

    def _extract_text(self, response: Any) -> str:
        """从响应中提取文本"""
        return response.choices[0].message.content or ""

    def _get_tool_call_id(self, response: Any) -> str:
        """获取工具调用ID"""
        try:
            return response.choices[0].message.tool_calls[0].id
        except (AttributeError, IndexError):
            return "call_unknown"

    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model="deepseek-embedding",
            input=texts,
        )
        return [item.embedding for item in response.data]

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 2)