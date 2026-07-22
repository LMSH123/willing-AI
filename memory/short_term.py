"""
乐意AI - 短期记忆

管理对话上下文窗口，控制Token使用量。
"""

from typing import List, Dict, Optional


class ShortTermMemory:
    """短期记忆 - 上下文窗口管理"""

    def __init__(self, max_tokens: int = 8000, reserve_tokens: int = 2000):
        """
        Args:
            max_tokens: 最大上下文token数
            reserve_tokens: 为回复预留的token数
        """
        self.max_tokens = max_tokens
        self.reserve_tokens = reserve_tokens

    @property
    def available_tokens(self) -> int:
        """可用于上下文的token数"""
        return self.max_tokens - self.reserve_tokens

    def trim_messages(
        self,
        messages: List[Dict],
        system_prompt: Optional[str] = None,
    ) -> List[Dict]:
        """
        裁剪消息列表到可用token范围内

        Args:
            messages: 完整消息列表
            system_prompt: 系统提示词

        Returns:
            裁剪后的消息列表
        """
        limit = self.available_tokens

        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})

        # 估算token数
        total = sum(len(m.get("content", "") or "") for m in result) // 2

        # 从后往前添加消息，直到达到上限
        for m in reversed(messages):
            content = m.get("content", "") or ""
            tokens = len(content) // 2
            if total + tokens > limit:
                break
            result.insert(1, m)
            total += tokens

        return result

    def estimate_tokens(self, text: str) -> int:
        """估算文本token数"""
        return max(1, len(text) // 2)