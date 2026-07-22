"""
乐意AI - CLI命令行界面

基于 rich 和 prompt_toolkit 构建的终端交互界面。
"""

import os
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from llm.base import BaseLLMClient
from conversation.session import ConversationSession
from conversation.history import save_session, load_session, list_sessions, delete_session
from conversation.system_prompts import get_system_prompt
from memory.long_term import LongTermMemory

console = Console()


class CLI:
    """乐意AI CLI 交互界面"""

    COMMANDS = {
        "/help": "显示帮助信息",
        "/new": "开始新对话",
        "/list": "列出所有对话历史",
        "/load": "加载指定对话 /load <id>",
        "/delete": "删除指定对话 /delete <id>",
        "/model": "显示当前模型信息",
        "/tools": "查看工具状态",
        "/doc": "导入文档到知识库 /doc <文件路径>",
        "/docs": "查看知识库状态",
        "/mem": "查看我的记忆",
        "/forget": "删除记忆 /forget <key>",
        "/clear": "清空当前对话内容",
        "/exit": "退出程序",
        "/quit": "退出程序",
    }

    def __init__(self, llm_client: BaseLLMClient, config: dict):
        self.llm = llm_client
        self.config = config
        self.session: Optional[ConversationSession] = None
        self.rag_retriever = None
        self.memory = LongTermMemory()

        # 初始化工具系统
        self.tool_registry = None
        self._init_tools()
        # 初始化RAG
        self._init_rag()

        self._new_session()
        self._setup_prompt()

    def _init_tools(self):
        """初始化工具注册"""
        tool_config = self.config.get("tools", {})
        if not tool_config.get("enabled", False):
            return

        from tools.registry import global_registry

        if tool_config.get("web_search", False):
            import tools.web_search  # noqa: F401
        if tool_config.get("calculator", False):
            import tools.calculator  # noqa: F401
        if tool_config.get("weather", False):
            import tools.weather  # noqa: F401

        self.tool_registry = global_registry

    def _init_rag(self):
        """初始化RAG检索器"""
        try:
            from knowledge.retriever import RAGRetriever
            knowledge_config = self.config.get("knowledge", {})
            self.rag_retriever = RAGRetriever(
                llm_client=self.llm,
                chunk_size=knowledge_config.get("chunk_size", 500),
                chunk_overlap=knowledge_config.get("chunk_overlap", 50),
                top_k=knowledge_config.get("top_k", 3),
            )
        except Exception as e:
            self.rag_retriever = None

    def _setup_prompt(self):
        """设置 prompt_toolkit"""
        history_path = self._get_data_path("cli_history.txt")
        self.prompt_session = PromptSession(
            history=FileHistory(history_path),
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
        )

    def _get_data_path(self, filename: str) -> str:
        """获取数据目录路径"""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, filename)

    def _new_session(self):
        """创建新会话"""
        tool_enabled = self.tool_registry is not None
        system_prompt = get_system_prompt()
        if tool_enabled:
            from conversation.system_prompts import TOOL_ENABLED_PROMPT
            from datetime import date
            today = date.today().isoformat()
            system_prompt += TOOL_ENABLED_PROMPT.format(current_date=today)
        self.session = ConversationSession(system_prompt=system_prompt)

    def run(self):
        """启动CLI主循环"""
        self._show_welcome()

        while True:
            try:
                text = self.prompt_session.prompt("\n你 > ")
            except (EOFError, KeyboardInterrupt):
                self._print("\n再见！", style="bold yellow")
                break

            text = text.strip()
            if not text:
                continue

            if text.startswith("/"):
                if self._handle_command(text):
                    continue
                else:
                    break

            self._handle_chat(text)

    def _show_welcome(self):
        """显示欢迎界面"""
        tool_status = ""
        if self.tool_registry:
            tools = self.tool_registry.list_tools()
            tool_names = [t.name for t in tools]
            tool_status = f"  |  工具: [green]{', '.join(tool_names)}[/green]"

        rag_status = ""
        if self.rag_retriever:
            stats = self.rag_retriever.get_stats()
            if stats["total_chunks"] > 0:
                rag_status = f"  |  知识库: [green]{stats['total_chunks']}文档块[/green]"

        console.print()
        console.print(Panel(
            "[bold cyan]乐意AI[/bold cyan] 已就绪  |  "
            f"模型: [green]{self.llm.model_name}[/green]  |  "
            f"后端: [yellow]{self.llm.backend_name}[/yellow]"
            f"{tool_status}{rag_status}\n\n"
            "输入 [bold]/help[/bold] 查看命令  |  "
            "[bold]/exit[/bold] 退出",
            title="[bold] 乐意AI [/bold]",
            border_style="cyan",
        ))

    def _print(self, text: str, **kwargs):
        """安全打印"""
        try:
            console.print(text, **kwargs)
        except UnicodeEncodeError:
            clean = text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
            print(clean)

    def _handle_command(self, text: str) -> bool:
        cmd = text.split()[0].lower()
        args = text.split()[1:] if len(text.split()) > 1 else []

        if cmd in ("/exit", "/quit"):
            self._print("再见！", style="bold yellow")
            return False

        elif cmd == "/help":
            self._show_help()
            return True

        elif cmd == "/new":
            self._new_session()
            self._print("已开始新对话", style="bold green")
            return True

        elif cmd == "/list":
            self._show_history()
            return True

        elif cmd == "/load":
            if args:
                self._load_conversation(args[0])
            else:
                self._print("用法: /load <session_id>", style="bold yellow")
            return True

        elif cmd == "/delete":
            if args:
                self._delete_conversation(args[0])
            else:
                self._print("用法: /delete <session_id>", style="bold yellow")
            return True

        elif cmd == "/model":
            self._print(
                f"后端: {self.llm.backend_name}  |  模型: {self.llm.model_name}",
                style="bold green",
            )
            return True

        elif cmd == "/tools":
            self._show_tools()
            return True

        elif cmd == "/doc":
            if args:
                self._add_document(args[0])
            else:
                self._print("用法: /doc <文件路径>", style="bold yellow")
            return True

        elif cmd == "/docs":
            self._show_docs()
            return True

        elif cmd == "/clear":
            self.session.clear()
            self._print("对话已清空", style="bold yellow")
            return True

        elif cmd == "/mem":
            self._show_memories()
            return True

        elif cmd == "/forget":
            if args:
                if self.memory.delete(args[0]):
                    self._print(f"已删除记忆: {args[0]}", style="bold yellow")
                else:
                    self._print(f"未找到记忆: {args[0]}", style="bold red")
            else:
                self._print("用法: /forget <key>", style="bold yellow")
            return True

        else:
            self._print(f"未知命令: {cmd}  |  输入 /help 查看可用命令", style="bold red")
            return True

    def _show_help(self):
        """显示帮助信息"""
        table = Table(title="命令列表", box=None)
        table.add_column("命令", style="bold cyan")
        table.add_column("说明", style="white")
        for cmd, desc in self.COMMANDS.items():
            table.add_row(cmd, desc)
        console.print(table)

    def _show_tools(self):
        """显示工具状态"""
        if not self.tool_registry:
            self._print("工具系统未启用（config.yaml 中 tools.enabled: true）", style="yellow")
            return

        tools = self.tool_registry.list_tools()
        if not tools:
            self._print("暂无已注册的工具", style="italic")
            return

        table = Table(title=f"已注册工具 ({len(tools)})", box=None)
        table.add_column("工具名", style="bold cyan")
        table.add_column("描述", style="white")
        for t in tools:
            table.add_row(t.name, t.description)
        console.print(table)

    def _show_history(self):
        """显示历史对话列表"""
        sessions = list_sessions(limit=20)
        if not sessions:
            self._print("暂无对话历史", style="italic")
            return

        table = Table(title="对话历史", box=None)
        table.add_column("ID", style="bold cyan", no_wrap=True)
        table.add_column("标题", style="white")
        table.add_column("消息数", justify="right")
        table.add_column("更新时间", style="dim")

        for s in sessions:
            session_id = s["session_id"]
            short_id = session_id[-12:] if len(session_id) > 12 else session_id
            table.add_row(
                short_id,
                s["title"],
                str(s["message_count"]),
                s["updated_at"][:16] if s["updated_at"] else "-",
            )
        console.print(table)

    def _load_conversation(self, session_id: str):
        """加载历史对话"""
        session = load_session(session_id)
        if not session:
            sessions = list_sessions(limit=100)
            for s in sessions:
                if s["session_id"].endswith(session_id):
                    session = load_session(s["session_id"])
                    break

        if session:
            self.session = session
            self._print(f"已加载对话: {session_id}", style="bold green")
            for msg in session.messages:
                role = "[bold cyan]你[/bold cyan]" if msg.role == "user" else "[bold green]乐意AI[/bold green]"
                self._print(f"\n{role} > {msg.content}")
        else:
            self._print(f"未找到对话: {session_id}", style="bold red")

    def _delete_conversation(self, session_id: str):
        """删除对话"""
        delete_session(session_id)
        self._print(f"已删除对话: {session_id}", style="bold yellow")

    def _add_document(self, file_path: str):
        """添加文档到知识库"""
        if not self.rag_retriever:
            self._print("RAG系统未初始化", style="bold red")
            return

        if not os.path.exists(file_path):
            self._print(f"文件不存在: {file_path}", style="bold red")
            return

        self._print(f"正在导入文档: {file_path}", style="yellow")
        result = self.rag_retriever.add_document(file_path)

        if result["success"]:
            self._print(
                f"导入成功！{result['source']} 已分为 {result['chunks']} 个文档块",
                style="bold green",
            )
        else:
            self._print(f"导入失败: {result.get('error', '未知错误')}", style="bold red")

    def _show_docs(self):
        """显示知识库状态"""
        if not self.rag_retriever:
            self._print("RAG系统未初始化", style="yellow")
            return

        stats = self.rag_retriever.get_stats()
        if stats["total_chunks"] == 0:
            self._print("知识库为空，使用 /doc <文件路径> 导入文档", style="italic")
            return

        self._print(f"知识库状态:", style="bold")
        self._print(f"  文档块数量: {stats['total_chunks']}")
        self._print(f"  检索深度: top-{stats['top_k']}")
        if stats["sources"]:
            self._print(f"  文档来源:")
            for src in stats["sources"]:
                self._print(f"    - {src}")

    def _show_memories(self):
        """显示记忆列表"""
        count = self.memory.count()
        if count == 0:
            self._print("暂无记忆，和我聊天时我会记住你的信息", style="italic")
            return

        memories = self.memory.get_all()
        table = Table(title=f"我的记忆 ({count})", box=None)
        table.add_column("键", style="bold cyan")
        table.add_column("内容", style="white")
        table.add_column("分类", style="dim")
        table.add_column("重要度", justify="right")

        for m in memories:
            importance = "⭐" * m.get("importance", 1)
            table.add_row(
                m["key"],
                m["content"][:40] + ("..." if len(m["content"]) > 40 else ""),
                m.get("category", ""),
                importance,
            )
        console.print(table)

    def _handle_chat(self, text: str):
        """处理用户输入并获取AI回复"""
        self.session.add_message("user", text)
        self._print(f"\n[bold cyan]你[/bold cyan] > {text}")

        # 加载相关记忆作为上下文
        memory_context = self.memory.get_relevant_context(text, max_memories=3)
        if memory_context:
            self.session.system_prompt = (
                self.session.system_prompt.split("\n## 记忆")[0]
                + f"\n## 记忆\n{memory_context}"
            )

        # 检查是否可调用RAG
        rag_answer = None
        if self.rag_retriever and self.rag_retriever.vector_store.count() > 0:
            rag_answer = self.rag_retriever.query(text)

        messages = self.session.get_context_window()
        self._print("\n[bold green]乐意AI[/bold green] > ", end="")

        try:
            full_response = ""

            if rag_answer:
                # 有知识库结果，直接使用RAG回答
                full_response = rag_answer
                console.print(full_response)
                try:
                    console.print(Markdown(full_response))
                except Exception:
                    self._print(full_response)
            elif self.tool_registry and self.tool_registry.has_tools():
                for chunk in self.llm.stream_chat_with_tools(
                    messages, self.tool_registry
                ):
                    full_response += chunk
                    console.print(chunk, end="")
                console.print()
                if full_response.strip():
                    try:
                        console.print(Markdown(full_response))
                    except Exception:
                        self._print(full_response)
            else:
                with Live(Spinner("dots", text="思考中..."), refresh_per_second=10, console=console) as live:
                    for chunk in self.llm.stream_chat(messages):
                        full_response += chunk
                        live.update(chunk)
                console.print()
                if full_response.strip():
                    try:
                        console.print(Markdown(full_response))
                    except Exception:
                        self._print(full_response)

            if full_response.strip():
                self.session.add_message("assistant", full_response)
                try:
                    save_session(self.session)
                except Exception:
                    pass

                # 尝试从对话中提取记忆
                try:
                    extracted = self.memory.extract_and_save(full_response, text)
                    if extracted > 0:
                        self._print(f"\n[dark_gray]💡 已记住 {extracted} 条新信息[/dark_gray]")
                except Exception:
                    pass

        except Exception as e:
            self._print(f"\n[bold red]出错了:[/bold red] {e}")
            self._print("提示: 请检查 .env 文件中的API密钥是否正确配置", style="italic")