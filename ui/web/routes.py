"""
乐意AI - Web API路由

FastAPI 路由，提供聊天、文档管理、对话历史等API接口。
支持 SSE (Server-Sent Events) 流式输出。
"""

import json
import os
import uuid
import base64
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from llm.base import BaseLLMClient
from conversation.session import ConversationSession
from conversation.history import save_session, load_session, list_sessions, delete_session
from conversation.system_prompts import get_system_prompt
from memory.long_term import LongTermMemory

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")
IMAGES_DIR = os.path.join(DATA_DIR, "images")

router = APIRouter()

# 全局引用（由 app.py 注入）
llm_client: Optional[BaseLLMClient] = None
tool_registry = None
rag_retriever = None

# 当前活跃会话
active_sessions: dict = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    images: List[str] = []  # base64 编码的图片列表


class ChatResponse(BaseModel):
    reply: str
    session_id: str


def get_or_create_session(session_id: Optional[str] = None) -> ConversationSession:
    """获取或创建会话"""
    if session_id and session_id in active_sessions:
        return active_sessions[session_id]

    # 从数据库加载
    if session_id:
        session = load_session(session_id)
        if session:
            active_sessions[session_id] = session
            return session

    # 创建新会话
    sid = session_id or datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    system_prompt = get_system_prompt()
    if tool_registry and tool_registry.has_tools():
        from conversation.system_prompts import TOOL_ENABLED_PROMPT
        system_prompt += TOOL_ENABLED_PROMPT
    session = ConversationSession(session_id=sid, system_prompt=system_prompt)
    active_sessions[sid] = session
    return session


@router.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "time": datetime.now().isoformat()}


@router.post("/chat")
async def chat(request: ChatRequest):
    """聊天接口（SSE流式），支持图片输入"""
    session = get_or_create_session(request.session_id)

    # 构建消息：如果有图片，使用多模态格式
    has_images = bool(request.images) and llm_client and llm_client.supports_vision

    if has_images:
        # 多模态消息：文本 + 图片
        multimodal_msg = BaseLLMClient.build_multimodal_message(request.message, request.images)
        session.add_message("user", f"[图片] {request.message}" if request.message else "[图片]")
        # 保存原始消息用于上下文
        messages = session.get_context_window()
        # 替换最后一条用户消息为多模态格式
        messages = messages[:-1] + multimodal_msg
    else:
        session.add_message("user", request.message)
        messages = session.get_context_window()

    async def generate():
        # 发送会话ID
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session.session_id})}\n\n"

        # 如果模型不支持视觉但用户发了图片，提示
        if request.images and not (llm_client and llm_client.supports_vision):
            yield f"data: {json.dumps({'type': 'chunk', 'content': '⚠️ 当前模型不支持图片识别，请切换到 gpt-4o-mini 或 gpt-4o 等视觉模型。'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'content': '⚠️ 当前模型不支持图片识别'})}\n\n"
            return

        full_response = ""

        try:
            if tool_registry and tool_registry.has_tools() and not has_images:
                # 带工具的流式对话（仅纯文本时使用工具）
                for chunk in llm_client.stream_chat_with_tools(messages, tool_registry):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            else:
                # 普通流式对话（含图片时自动走此分支）
                for chunk in llm_client.stream_chat(messages):
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # 保存回复
            if full_response.strip():
                session.add_message("assistant", full_response)
                try:
                    save_session(session)
                except Exception:
                    pass

            yield f"data: {json.dumps({'type': 'done', 'content': full_response})}\n\n"

        except Exception as e:
            error_msg = str(e)
            # 处理 API 密钥不支持多模态的情况
            if "403" in error_msg or "do not support multimodal" in error_msg.lower() or "does not support image" in error_msg.lower():
                error_msg = (
                    "⚠️ 当前 API 密钥不支持图片识别功能。\n\n"
                    "可能的原因：\n"
                    "1. **ChatAnywhere 免费版** 不支持图片分析，需要付费密钥\n"
                    "2. 其他后端可能需要单独的视觉模型配额\n\n"
                    "建议：\n"
                    "• 使用 OpenAI 官方密钥直接连接\n"
                    "• 或切换到支持视觉的模型后端"
                )
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations")
async def list_conversations():
    """列出对话历史"""
    sessions = list_sessions(limit=50)
    return {"conversations": sessions}


@router.get("/conversations/{session_id}")
async def get_conversation(session_id: str):
    """获取单个对话"""
    session = load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="对话不存在")
    return {
        "session_id": session.session_id,
        "messages": [{"role": m.role, "content": m.content[:200]} for m in session.messages],
        "message_count": len(session.messages),
    }


@router.delete("/conversations/{session_id}")
async def delete_conversation(session_id: str):
    """删除对话"""
    delete_session(session_id)
    if session_id in active_sessions:
        del active_sessions[session_id]
    return {"success": True}


@router.post("/conversations/new")
async def new_conversation():
    """创建新对话"""
    session = get_or_create_session()
    return {"session_id": session.session_id}


@router.get("/model")
async def get_model_info():
    """获取模型信息"""
    if not llm_client:
        return {"backend": "unknown", "model": "unknown", "supports_vision": False}
    return {
        "backend": llm_client.backend_name,
        "model": llm_client.model_name,
        "supports_vision": llm_client.supports_vision,
    }


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """上传图片，返回 base64 编码"""
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"]
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的图片类型: {file.content_type}，支持 JPG/PNG/GIF/WebP")

    content = await file.read()

    # 限制文件大小（10MB）
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片太大，请上传小于 10MB 的图片")

    # 保存到本地
    os.makedirs(IMAGES_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex[:8]}.{ext}"
    file_path = os.path.join(IMAGES_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # 返回 base64
    b64_data = base64.b64encode(content).decode("utf-8")

    return {
        "success": True,
        "filename": filename,
        "base64": b64_data,
        "size": len(content),
        "mime": file.content_type or "image/jpeg",
    }


@router.get("/tools")
async def get_tools():
    """获取工具列表"""
    if not tool_registry:
        return {"tools": []}
    return {
        "tools": [
            {"name": t.name, "description": t.description}
            for t in tool_registry.list_tools()
        ]
    }


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档"""
    if not rag_retriever:
        raise HTTPException(status_code=400, detail="RAG系统未初始化")

    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    file_path = os.path.join(DOCUMENTS_DIR, file.filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    result = rag_retriever.add_document(file_path)
    return result


@router.get("/documents")
async def list_documents():
    """列出知识库文档"""
    if not rag_retriever:
        return {"sources": [], "total_chunks": 0}
    stats = rag_retriever.get_stats()
    return {
        "sources": stats["sources"],
        "total_chunks": stats["total_chunks"],
    }


@router.get("/knowledge")
async def get_knowledge_stats():
    """获取知识库统计"""
    if not rag_retriever:
        return {"enabled": False, "total_chunks": 0, "sources": []}
    stats = rag_retriever.get_stats()
    return {"enabled": True, **stats}


def init_app(llm, tools, rag):
    """注入全局依赖"""
    global llm_client, tool_registry, rag_retriever
    llm_client = llm
    tool_registry = tools
    rag_retriever = rag


# 记忆系统
_memory = LongTermMemory()


@router.get("/memories")
async def list_memories():
    """列出所有记忆"""
    memories = _memory.get_all()
    return {"memories": memories, "count": len(memories)}


@router.delete("/memories/{key}")
async def delete_memory(key: str):
    """删除记忆"""
    ok = _memory.delete(key)
    return {"success": ok}


@router.post("/memories")
async def save_memory(key: str = Form(...), content: str = Form(...), category: str = Form("general")):
    """保存记忆"""
    ok = _memory.save(key, content, category, importance=3)
    return {"success": ok}