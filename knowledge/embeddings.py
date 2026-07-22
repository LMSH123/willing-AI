"""
乐意AI - 嵌入服务

使用LLM客户端的embed方法生成文本嵌入向量。
"""

from typing import List, Optional
from llm.base import BaseLLMClient


class EmbeddingService:
    """嵌入服务"""

    def __init__(self, llm_client: BaseLLMClient):
        self.llm = llm_client
        self._cache = {}

    def embed(self, text: str) -> List[float]:
        """
        生成单个文本的嵌入向量

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        # 使用缓存
        cache_key = text[:200]  # 用前200字符做key
        if cache_key in self._cache:
            return self._cache[cache_key]

        vectors = self.embed_batch([text])
        if vectors:
            self._cache[cache_key] = vectors[0]
            return vectors[0]
        return []

    def embed_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        批量生成嵌入向量

        Args:
            texts: 文本列表
            batch_size: 每批处理数量

        Returns:
            嵌入向量列表
        """
        all_vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                vectors = self.llm.embed(batch)
                all_vectors.extend(vectors)
            except Exception as e:
                print(f"嵌入生成失败: {e}")
                all_vectors.extend([[] for _ in batch])
        return all_vectors

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()