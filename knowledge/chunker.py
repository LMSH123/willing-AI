"""
乐意AI - 文本分块器

将长文档分割成适合检索的文本块。
"""

from typing import List, Optional
from .loader import Document


def chunk_document(
    doc: Document,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: Optional[List[str]] = None,
) -> List[Document]:
    """
    将文档分割成文本块

    Args:
        doc: 原始文档
        chunk_size: 每块目标字符数
        chunk_overlap: 块之间重叠字符数
        separators: 分隔符优先级列表

    Returns:
        文本块列表
    """
    if separators is None:
        separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " "]

    text = doc.content
    if not text:
        return []

    chunks = _split_text(text, chunk_size, chunk_overlap, separators)

    result = []
    for i, chunk_text in enumerate(chunks):
        chunk_meta = {**doc.metadata, "chunk_index": i, "chunk_total": len(chunks)}
        result.append(Document(content=chunk_text, metadata=chunk_meta))

    return result


def _split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    separators: List[str],
) -> List[str]:
    """
    递归分割文本

    优先在段落/句子边界处分割，避免切碎语义单元。
    """
    if len(text) <= chunk_size:
        return [text]

    # 尝试用分隔符分割
    for sep in separators:
        if sep in text:
            segments = text.split(sep)
            chunks = _merge_segments(segments, sep, chunk_size, chunk_overlap)
            if chunks:
                return chunks

    # 没有分隔符，直接按字符切
    return _split_by_chars(text, chunk_size, chunk_overlap)


def _merge_segments(
    segments: List[str],
    separator: str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[str]:
    """将片段合并成合适大小的块"""
    chunks = []
    current_chunk = ""
    overlap_buffer = ""

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        # 如果加上当前段会超长，先保存当前块
        if current_chunk and len(current_chunk) + len(separator) + len(seg) > chunk_size:
            chunks.append(current_chunk.strip())

            # 重叠部分：从当前块尾部取 overlap 字符
            overlap_buffer = current_chunk[-chunk_overlap:].strip() if chunk_overlap > 0 else ""
            current_chunk = overlap_buffer + separator if overlap_buffer else ""

        if current_chunk:
            current_chunk += separator + seg
        else:
            current_chunk = seg

    # 最后一块
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _split_by_chars(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """直接按字符数分割"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start = end - chunk_overlap
        if start < 0:
            start = 0
    return [c for c in chunks if c]