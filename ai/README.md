# 行知 AI 核心包 (xingzhi-ai)

行知智慧文旅平台的 AI 核心模块，提供 DeepSeek 客户端、系统 Prompt 管理和上下文裁剪能力。

## 职责

- **DeepSeek 客户端**：基于 `AsyncOpenAI` 的异步调用封装
- **系统提示词**：旅游助手角色定义和回答规范
- **上下文管理**：多轮对话历史消息的裁剪和组装
- **异常定义**：AI 层专用异常类型

本包**不依赖** FastAPI、SQLAlchemy 或项目数据库模型，保持独立可测试。

## 与 backend 的关系

- `backend/app/services/ai_service.py` 作为适配层：
  - 从数据库读取历史消息
  - 调用本包的 `DeepSeekChatClient`、`build_system_prompt`、`trim_context`
  - 将 AI 异常转换为 FastAPI HTTP 异常
- `backend/app/api/ai.py` 负责路由、JWT 认证和 HTTP 响应

## 安装

新成员从零搭建开发环境的完整步骤：

```bash
# 1. 安装后端依赖（含 openai、FastAPI 等）
cd backend
pip install -r requirements.txt

# 2. 安装 AI 核心包（editable 模式，代码修改即时生效）
cd ..
pip install -e ./ai
```

如果只更新 AI 包（后端依赖已安装），直接从项目根目录执行：

```bash
pip install -e ./ai
```

## 所需环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（必填） | — |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-v4-flash` |
| `DEEPSEEK_TIMEOUT_SECONDS` | 请求超时（秒） | `30` |

## 启动方式

### 从 backend 目录启动（推荐）

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 从项目根目录启动

```bash
uvicorn backend.main:app --reload --port 8000
```

两种方式均依赖 `backend/.env` 中的 `DEEPSEEK_API_KEY`。

## 测试

```bash
# 安装开发依赖
pip install -e "ai/[dev]"

# 运行 AI 包测试
pytest ai/tests/

# 运行后端测试
pytest backend/tests/
```

## 当前限制

### 多轮上下文

当前**不修改** `ai_sessions` 表结构。多轮对话通过查询当前用户最近 20 条消息（最多 8000 字符）构建上下文。

**已知局限**：
- 如果用户穿插多个不同话题的消息，上下文会混在一起
- 不支持按会话分组（`ai_sessions` 表缺少 `conversation_id` 字段）

### session_id 兼容性

API 请求中的 `session_id` 字段仅用于前端协议兼容，后端不按其查询或隔离消息。返回的 `session_id` 实际为当前用户消息的数据库 `id`。

真正的多会话隔离需要在后续版本中引入 `conversation_id` 或独立会话表。

## 安全

- **禁止提交 `.env` 文件**（已被 `.gitignore` 忽略）
- `.env.example` 只包含变量名和默认值示例，不含真实密钥
- 日志不得输出 `DEEPSEEK_API_KEY`、数据库密码或 JWT Secret
