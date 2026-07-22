"""
乐意AI - 向量存储

使用 ChromaDB 实现文档向量的存储与检索。
"""

import os
from typing import List, Optional, Dict

import chromadb
from chromadb.config import Settings

from .loader import Document

# 向量数据库存储路径
VECTOR_STORE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "vector_store",
)


class VectorStore:
    """向量存储"""

    def __init__(self, collection_name: str = "documents"):
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=VECTOR_STORE_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(
        self,
        chunks: List[Document],
        embeddings: List[List[float]],
    ) -> List[str]:
        """
        添加文档块到向量库

        Args:
            chunks: 文档块列表
            embeddings: 对应的嵌入向量列表

        Returns:
            添加的ID列表
        """
        if not chunks or not embeddings:
            return []

        ids = []
        documents = []
        metadatas = []

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            if not chunk.content.strip():
                continue
            doc_id = f"{chunk.metadata.get('source', 'doc')}_{i}"
            ids.append(doc_id)
            documents.append(chunk.content)
            metadatas.append({
                "source": chunk.metadata.get("source", ""),
                "chunk_index": str(chunk.metadata.get("chunk_index", 0)),
                "chunk_total": str(chunk.metadata.get("chunk_total", 0)),
            })

        if not ids:
            return []

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 3,
    ) -> List[Dict]:
        """
        搜索最相似的文档块

        Args:
            query_embedding: 查询的嵌入向量
            top_k: 返回结果数量

        Returns:
            [{"content": str, "source": str, "score": float}, ...]
        """
        if not query_embedding:
            return []

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
        )

        items = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                items.append({
                    "content": results["documents"][0][i],
                    "source": results["metadatas"][0][i].get("source", ""),
                    "score": float(results["distances"][0][i]) if results.get("distances") else 0.0,
                })
        return items

    def count(self) -> int:
        """获取文档块数量"""
        return self.collection.count()

    def delete_collection(self):
        """删除整个集合"""
        try:
            self.client.delete_collection(self.collection.name)
        except Exception:
            pass

    def list_sources(self) -> List[str]:
        """列出所有文档来源"""
        results = self.collection.get()
        sources = set()
        for meta in results.get("metadatas", []):
            src = meta.get("source", "")
            if src:
                sources.add(src)
        return sorted(sources)