"""
乐意AI - 检索器 (RAG Pipeline)

将文档加载、分块、嵌入、存储、检索串联成完整的RAG流程。
"""

import os
from typing import List, Optional, Dict

from llm.base import BaseLLMClient
from .loader import Document, load_document, load_documents, list_documents
from .chunker import chunk_document
from .embeddings import EmbeddingService
from .vector_store import VectorStore

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")


class RAGRetriever:
    """RAG检索器 - 完整的检索增强生成流程"""

    def __init__(
        self,
        llm_client: BaseLLMClient,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        top_k: int = 3,
    ):
        self.llm = llm_client
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k

        self.embeddings = EmbeddingService(llm_client)
        self.vector_store = VectorStore()
        os.makedirs(DOCUMENTS_DIR, exist_ok=True)

    def add_document(self, file_path: str) -> Dict:
        """
        加载并索引一个文档

        Args:
            file_path: 文件路径

        Returns:
            {"success": bool, "chunks": int, "source": str, "error": str}
        """
        # 如果文件不在documents目录，复制过去
        dest_path = self._ensure_in_docs_dir(file_path)

        doc = load_document(dest_path)
        if doc is None:
            return {"success": False, "error": "文件不存在", "source": os.path.basename(dest_path), "chunks": 0}
        if not doc.content:
            return {"success": False, "error": doc.metadata.get("error", "文件为空"), "source": os.path.basename(dest_path), "chunks": 0}

        # 分块
        chunks = chunk_document(doc, self.chunk_size, self.chunk_overlap)
        if not chunks:
            return {"success": False, "error": "分块后内容为空", "source": os.path.basename(dest_path), "chunks": 0}

        # 生成嵌入
        texts = [c.content for c in chunks]
        vectors = self.embeddings.embed_batch(texts)

        # 存入向量库
        ids = self.vector_store.add_documents(chunks, vectors)

        return {
            "success": True,
            "source": os.path.basename(dest_path),
            "chunks": len(ids),
            "error": "",
        }

    def add_documents(self, file_paths: List[str]) -> List[Dict]:
        """批量添加文档"""
        return [self.add_document(p) for p in file_paths]

    def add_all_from_docs_dir(self) -> List[Dict]:
        """添加documents目录下所有文档"""
        files = list_documents(DOCUMENTS_DIR)
        return self.add_documents(files) if files else []

    def query(self, question: str) -> str:
        """
        基于知识库回答用户问题

        Args:
            question: 用户问题

        Returns:
            AI回答（带上下文引用）
        """
        if self.vector_store.count() == 0:
            return ""

        # 1. 生成问题嵌入
        query_vector = self.embeddings.embed(question)
        if not query_vector:
            return ""

        # 2. 检索相关文档块
        results = self.vector_store.search(query_vector, top_k=self.top_k)
        if not results:
            return ""

        # 3. 构建上下文
        context_parts = []
        for i, r in enumerate(results, 1):
            source = r.get("source", "未知来源")
            context_parts.append(f"[来源 {i}: {source}]\n{r['content']}")

        context = "\n\n---\n\n".join(context_parts)

        # 4. 构建RAG提示
        sources = [r["source"] for r in results if r.get("source")]
        source_str = ", ".join(set(sources))

        system_prompt = (
            "你是一个知识库问答助手。请根据以下提供的文档内容回答用户问题。\n\n"
            f"参考文档（来自: {source_str}）:\n{context}\n\n"
            "回答要求:\n"
            "- 如果文档内容能回答问题，请基于文档给出准确答案\n"
            "- 如果文档内容不足以回答问题，请说明'文档中没有相关信息'\n"
            "- 不要编造不在文档中的信息\n"
            "- 引用具体来源使回答更有说服力"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        # 5. 生成回答
        try:
            answer = self.llm.chat(messages)
            return answer
        except Exception as e:
            return f"生成回答时出错: {e}"

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        return {
            "total_chunks": self.vector_store.count(),
            "sources": self.vector_store.list_sources(),
            "top_k": self.top_k,
        }

    def _ensure_in_docs_dir(self, file_path: str) -> str:
        """确保文件在documents目录中"""
        abs_path = os.path.abspath(file_path)
        if os.path.dirname(abs_path) == os.path.abspath(DOCUMENTS_DIR):
            return abs_path

        # 复制到documents目录
        import shutil
        dest = os.path.join(DOCUMENTS_DIR, os.path.basename(abs_path))
        if abs_path != dest:
            try:
                shutil.copy2(abs_path, dest)
            except Exception:
                pass
        return dest