# 乐意AI - 个人AI助手

基于云端大模型API的个人AI助手，支持多后端切换，CLI + Web 双界面。

## 功能特性

- 💬 **智能对话**：多轮对话，上下文管理，历史记录持久化
- 🔍 **联网搜索**：AI可联网获取最新信息
- 🧮 **工具调用**：计算器、天气查询等外部工具
- 📚 **知识库RAG**：上传PDF/Word/TXT文档，基于内容问答
- 🧠 **记忆系统**：长期记忆用户偏好和关键信息
- 🎨 **双界面**：命令行(CLI) + 网页(Web) 两种使用方式
- 🔄 **多后端**：支持 ChatAnywhere / DeepSeek / OpenAI / GitHub Models 一键切换

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取免费API密钥

本项目默认使用 **ChatAnywhere** 免费API中转（由 [GPT_API_free](https://github.com/chatanywhere/GPT_API_free) 提供）：

1. 访问 https://api.chatanywhere.tech/v1/oauth/free/render
2. 绑定GitHub账号获取免费API Key
3. 复制得到的 Key（`sk-` 开头）

### 3. 配置API密钥

```bash
cp .env.example .env
```

编辑 `.env`，填入你的API Key：

```
OPENAI_API_KEY=sk-你的密钥
```

### 4. 启动

**Web模式（推荐）：**
```bash
python app.py
# 访问 http://localhost:8000
```

**CLI模式：**
```bash
python main.py
```

## 配置说明

编辑 `config.yaml` 可调整：

| 配置项 | 说明 | 可选值 |
|--------|------|--------|
| `llm.backend` | 后端引擎 | `chatanywhere`(推荐), `deepseek`, `openai`, `github` |
| `llm.model` | 模型名称 | `gpt-4o-mini`, `deepseek-chat`, `deepseek-r1` 等 |

### 免费模型每日次数限制（ChatAnywhere）

| 模型 | 每日限制 |
|------|---------|
| gpt-4o-mini / gpt-3.5-turbo | 200次 |
| deepseek-r1 / deepseek-v3 | 30次 |
| gpt-4o / gpt-4.1 | 5次 |

## 项目结构

```
乐意AI/
├── main.py              # CLI入口
├── app.py               # Web入口
├── config.yaml          # 配置文件
├── .env.example         # API密钥模板
├── llm/                 # 大模型客户端（多后端抽象）
├── conversation/        # 对话管理
├── memory/              # 记忆系统
├── knowledge/           # 知识库RAG
├── tools/               # 工具系统（搜索/计算器/天气）
├── ui/                  # 用户界面（CLI + Web）
└── data/                # 数据存储（自动生成）
```

## 许可

MIT License