"""
乐意AI - Web应用入口

启动 FastAPI 服务器，提供 Web 界面。
"""

import sys
import os
import argparse
import time

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 修复 Windows Python 3.13 socket._fallback_socketpair 问题
import socket
_original_socketpair = socket.socketpair if hasattr(socket, 'socketpair') else None
if _original_socketpair:
    def _patched_socketpair(*args, **kwargs):
        try:
            return _original_socketpair(*args, **kwargs)
        except (ConnectionError, OSError):
            # 回退方案：使用 AF_INET 创建 socketpair
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            a.connect(listener.getsockname())
            time.sleep(0.01)
            b, _ = listener.accept()
            listener.close()
            return a, b
    socket.socketpair = _patched_socketpair

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="乐意AI", version="0.1.0")


def create_app(config_path: str = None) -> FastAPI:
    """创建并配置FastAPI应用"""
    import yaml
    from llm.factory import create_llm
    from tools.registry import global_registry
    from ui.web.routes import init_app as init_routes, router

    cfg_path = config_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    llm = create_llm(config)

    tool_config = config.get("tools", {})
    tools = None
    if tool_config.get("enabled", False):
        if tool_config.get("web_search", False):
            import tools.web_search
        if tool_config.get("calculator", False):
            import tools.calculator
        if tool_config.get("weather", False):
            import tools.weather
        tools = global_registry

    rag = None
    try:
        from knowledge.retriever import RAGRetriever
        knowledge_config = config.get("knowledge", {})
        rag = RAGRetriever(
            llm_client=llm,
            chunk_size=knowledge_config.get("chunk_size", 500),
            chunk_overlap=knowledge_config.get("chunk_overlap", 50),
            top_k=knowledge_config.get("top_k", 3),
        )
    except Exception:
        pass

    init_routes(llm, tools, rag)
    app.include_router(router, prefix="/api")

    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "web", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "web", "templates")

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(templates_dir, "chat.html"))

    @app.get("/chat")
    async def chat_page():
        return FileResponse(os.path.join(templates_dir, "chat.html"))

    return app


def main():
    parser = argparse.ArgumentParser(description="乐意AI - Web服务器")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    parser.add_argument("--config", default=None, help="配置文件路径")
    args = parser.parse_args()

    if args.config:
        cfg_path = args.config
    else:
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

    import yaml
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    web_config = config.get("ui", {}).get("web", {})
    host = args.host or web_config.get("host", "127.0.0.1")
    port = args.port or web_config.get("port", 8000)

    app = create_app(cfg_path)

    print(f"\n  乐意AI Web 服务已启动")
    print(f"  http://{host}:{port}")
    print(f"  按 Ctrl+C 停止服务\n")

    # 使用 Config + Server 模式启动
    cfg = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(cfg)
    server.run()


if __name__ == "__main__":
    main()