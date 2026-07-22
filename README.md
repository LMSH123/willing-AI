# 乐意AI - 个人AI助手

基于云端大模型API的个人AI助手，支持多后端切换，CLI + Web 双界面。

## 功能特性

- 💬 **智能对话**：多轮对话，上下文管理，历史记录持久化
- 🔍 **联网搜索**：AI可自动联网获取最新信息（2023年后的事件强制搜索）
- 🖼️ **图片识别**：上传图片，AI自动识别内容（需视觉模型支持）
- 🧮 **工具调用**：计算器、天气查询等外部工具
- 📚 **知识库RAG**：上传PDF/Word/TXT文档，基于内容问答
- 🧠 **记忆系统**：长期记忆用户偏好和关键信息
- 📅 **知道日期**：AI知道今天的真实日期，不再回答2023年
- 🎨 **双界面**：命令行(CLI) + 网页(Web) 两种使用方式
- 🔄 **多后端**：支持 GitHub Models / ChatAnywhere / DeepSeek / OpenAI 一键切换

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取免费API密钥

**推荐方案：GitHub Models（免费，1500次/天，支持看图）**

1. 使用 GitHub 账号登录 https://github.com/marketplace/models
2. 创建一个 Personal Access Token：https://github.com/settings/tokens
3. 复制 token，填入 `.env` 的 `GITHUB_API_KEY`

**备选方案：ChatAnywhere（免费，200次/天，纯文字）**

1. 访问 https://api.chatanywhere.tech/v1/oauth/free/render
2. 绑定GitHub账号获取免费API Key
3. 复制得到的 Key（`sk-` 开头）

### 3. 配置API密钥

```bash
cp .env.example .env
```

编辑 `.env`，填入你的API Key：

```
# GitHub Models（推荐，1500次/天，支持看图）
GITHUB_API_KEY=你的github_token

# 或 ChatAnywhere（免费，200次/天，纯文字）
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
| `llm.backend` | 后端引擎 | `github`(推荐), `chatanywhere`, `deepseek`, `openai` |
| `llm.model` | 模型名称 | `gpt-4o-mini`, `gpt-4o`, `deepseek-chat`, `deepseek-r1` 等 |

### 各后端额度对比

| 后端 | 模型 | 每日额度 | 看图 |
|------|------|---------|------|
| GitHub Models | gpt-4o-mini | **1500次** | ✅ |
| GitHub Models | gpt-4o | 500次 | ✅ |
| ChatAnywhere | gpt-4o-mini | 200次 | ❌ |
| ChatAnywhere | deepseek-r1/v3 | 30次 | ❌ |
| OpenAI | gpt-4o-mini | 付费按量 | ✅ |

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