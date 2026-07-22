"""
乐意AI - 对话管理模块

管理多轮对话的消息列表、上下文窗口和系统提示词。
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """单条消息"""
    role: str  # system / user / assistant / tool
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {"role": self.role, "content": self.content}

    @staticmethod
    def from_dict(data: Dict) -> "Message":
        return Message(role=data["role"], content=data["content"])


class ConversationSession:
    """对话会话 - 管理消息列表和上下文窗口"""

    def __init__(
        self,
        session_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_context_tokens: int = 8000,
    ):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.system_prompt = system_prompt
        self.max_context_tokens = max_context_tokens
        self.messages: List[Message] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def add_message(self, role: str, content: str):
        """添加一条消息"""
        self.messages.append(Message(role=role, content=content))
        self.updated_at = datetime.now().isoformat()

    def get_messages(self, include_system: bool = True) -> List[Dict]:
        """
        获取消息列表（用于API调用）

        Args:
            include_system: 是否包含系统提示词

        Returns:
            消息字典列表
        """
        result = []
        if include_system and self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        result.extend([m.to_dict() for m in self.messages])
        return result

    def get_context_window(self, max_tokens: int = None) -> List[Dict]:
        """
        获取上下文窗口内的消息（滑动窗口策略）

        保留最近的对话，直到达到token上限。
        """
        limit = max_tokens or self.max_context_tokens
        messages = self.get_messages()
        total = sum(len(m["content"]) for m in messages) // 2  # 粗略估算

        if total <= limit:
            return messages

        # 从后往前裁剪，保留系统提示词和最近的消息
        kept = [messages[0]] if self.system_prompt else []
        kept_tokens = sum(len(m["content"]) for m in kept) // 2

        for m in reversed(messages[1:] if self.system_prompt else messages):
            tokens = len(m["content"]) // 2
            if kept_tokens + tokens > limit:
                break
            kept.insert(1, m)
            kept_tokens += tokens

        return kept

    def clear(self):
        """清空对话历史"""
        self.messages.clear()
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "system_prompt": self.system_prompt,
            "max_context_tokens": self.max_context_tokens,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ConversationSession":
        session = cls(
            session_id=data.get("session_id"),
            system_prompt=data.get("system_prompt"),
            max_context_tokens=data.get("max_context_tokens", 8000),
        )
        session.messages = [Message.from_dict(m) for m in data.get("messages", [])]
        session.created_at = data.get("created_at", session.created_at)
        session.updated_at = data.get("updated_at", session.updated_at)
        return session