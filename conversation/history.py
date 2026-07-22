"""
乐意AI - 对话历史存储

使用SQLite持久化存储对话记录。
"""

import sqlite3
import json
import os
from typing import List, Optional, Dict
from datetime import datetime

from .session import ConversationSession

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "conversations.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            title TEXT DEFAULT '新对话',
            system_prompt TEXT,
            max_context_tokens INTEGER DEFAULT 8000,
            message_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES conversations(session_id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def save_session(session: ConversationSession):
    """保存会话及其消息到数据库"""
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO conversations
           (session_id, title, system_prompt, max_context_tokens, message_count, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            session.session_id,
            _generate_title(session),
            session.system_prompt,
            session.max_context_tokens,
            len(session.messages),
            session.created_at,
            session.updated_at,
        ),
    )
    # 删除旧消息，重新插入
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session.session_id,))
    for msg in session.messages:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session.session_id, msg.role, msg.content, msg.timestamp),
        )
    conn.commit()
    conn.close()


def load_session(session_id: str) -> Optional[ConversationSession]:
    """从数据库加载会话"""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM conversations WHERE session_id = ?", (session_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None

    session = ConversationSession(
        session_id=row["session_id"],
        system_prompt=row["system_prompt"],
        max_context_tokens=row["max_context_tokens"],
    )
    session.created_at = row["created_at"]
    session.updated_at = row["updated_at"]

    # 加载消息
    rows = conn.execute(
        "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()
    for msg_row in rows:
        from .session import Message
        session.messages.append(
            Message(role=msg_row["role"], content=msg_row["content"], timestamp=msg_row["timestamp"])
        )

    conn.close()
    return session


def list_sessions(limit: int = 20) -> List[Dict]:
    """列出最近的会话列表"""
    conn = get_db()
    rows = conn.execute(
        """SELECT session_id, title, message_count, created_at, updated_at
           FROM conversations ORDER BY updated_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_session(session_id: str):
    """删除会话"""
    conn = get_db()
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def _generate_title(session: ConversationSession) -> str:
    """根据第一条用户消息生成标题"""
    if session.messages:
        for msg in session.messages:
            if msg.role == "user":
                content = msg.content.strip()
                if len(content) > 30:
                    return content[:30] + "..."
                return content
    return "新对话"


# 初始化数据库
init_db()