"""
乐意AI - 长期记忆

使用SQLite存储用户偏好、关键信息、重要事实。
支持按相关性检索和重要性评分。
"""

import sqlite3
import os
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime

# 数据库路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "memory.db")


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            importance INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            access_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_category
        ON memories(category)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_importance
        ON memories(importance DESC)
    """)
    conn.commit()
    conn.close()


class LongTermMemory:
    """长期记忆系统"""

    def __init__(self):
        init_db()

    def save(self, key: str, content: str, category: str = "general", importance: int = 1) -> bool:
        """
        保存一条记忆

        Args:
            key: 记忆键名（如 'user_name', 'user_location'）
            content: 记忆内容
            category: 分类（general, preference, fact, personal）
            importance: 重要性 1-5

        Returns:
            是否成功
        """
        if not key or not content:
            return False

        now = datetime.now().isoformat()
        conn = get_db()
        try:
            conn.execute(
                """INSERT INTO memories (key, content, category, importance, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       content = excluded.content,
                       category = excluded.category,
                       importance = excluded.importance,
                       updated_at = excluded.updated_at""",
                (key, content, category, importance, now, now),
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"保存记忆失败: {e}")
            return False
        finally:
            conn.close()

    def get(self, key: str) -> Optional[Dict]:
        """获取单条记忆"""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM memories WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        if row:
            # 更新访问计数
            self._increment_access(key)
            return dict(row)
        return None

    def delete(self, key: str) -> bool:
        """删除记忆"""
        conn = get_db()
        conn.execute("DELETE FROM memories WHERE key = ?", (key,))
        deleted = conn.total_changes > 0
        conn.commit()
        conn.close()
        return deleted

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        搜索记忆（关键词匹配）

        Args:
            query: 搜索关键词
            limit: 返回数量

        Returns:
            匹配的记忆列表
        """
        conn = get_db()
        # 关键词搜索
        words = query.split()
        conditions = []
        params = []
        for word in words:
            if len(word) < 2:
                continue
            conditions.append("(key LIKE ? OR content LIKE ?)")
            params.extend([f"%{word}%", f"%{word}%"])

        if not conditions:
            # 无有效关键词，返回最近记忆
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            sql = f"SELECT * FROM memories WHERE {' OR '.join(conditions)} ORDER BY importance DESC, updated_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()

        conn.close()
        return [dict(r) for r in rows]

    def get_all(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """获取所有记忆"""
        conn = get_db()
        if category:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category = ? ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_relevant_context(self, query: str, max_memories: int = 5) -> str:
        """
        获取与查询相关的记忆作为上下文

        Args:
            query: 当前用户输入
            max_memories: 最多返回的记忆数

        Returns:
            格式化的记忆文本
        """
        memories = self.search(query, limit=max_memories)
        if not memories:
            return ""

        lines = []
        for m in memories:
            category = m.get("category", "general")
            content = m.get("content", "")
            lines.append(f"[{category}] {content}")

        if lines:
            return "我知道关于你的一些信息:\n" + "\n".join(lines)
        return ""

    def extract_and_save(self, text: str, user_message: str = "") -> int:
        """
        从对话中提取重要信息并保存为记忆

        Args:
            text: AI回复文本
            user_message: 用户消息（用于上下文）

        Returns:
            新保存的记忆数量
        """
        saved = 0

        # 模式1: "我叫XXX" / "我是XXX" / "我的名字是XXX"
        patterns = [
            (r"(?:我叫|我是|我的名字是|你可以叫我)\s*(.{1,20})", "personal", 5),
            (r"(?:我住在|我在|我来自|我家在)\s*(.{1,20})", "personal", 4),
            (r"(?:我喜欢|我爱|我爱好|我的爱好是)\s*(.{1,20})", "preference", 3),
            (r"(?:我工作|我的工作是|我是做|我的职业是)\s*(.{1,20})", "personal", 4),
            (r"(?:我今年|我\s*(\d+)\s*岁|年龄)", "personal", 3),
        ]

        for pattern, category, importance in patterns:
            match = re.search(pattern, user_message)
            if match:
                # 提取关键信息生成key
                content = match.group(0).strip()
                key = f"user_{category}"
                if self.save(key, content, category, importance):
                    saved += 1

        # 模式2: 从AI回复中提取确认的信息
        confirm_patterns = [
            r"(?:记住了|已记住|我记住|我会记住)\s*(.{1,50})",
            r"(?:好的|明白|知道了)\s*[,，]\s*(.{1,50})",
        ]
        for pattern in confirm_patterns:
            match = re.search(pattern, text)
            if match:
                content = match.group(0).strip()
                key = f"confirmed_{datetime.now().timestamp()}"
                if self.save(key, content, "general", 2):
                    saved += 1

        return saved

    def count(self) -> int:
        """获取记忆总数"""
        conn = get_db()
        count = conn.execute("SELECT COUNT(*) as c FROM memories").fetchone()["c"]
        conn.close()
        return count

    def clear_all(self):
        """清空所有记忆"""
        conn = get_db()
        conn.execute("DELETE FROM memories")
        conn.commit()
        conn.close()

    def _increment_access(self, key: str):
        """增加访问计数"""
        conn = get_db()
        conn.execute(
            "UPDATE memories SET access_count = access_count + 1 WHERE key = ?",
            (key,),
        )
        conn.commit()
        conn.close()


# 初始化
init_db()