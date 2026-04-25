# AI Enterprise Assistant Backend

纯后端FastAPI项目，从Next.js全栈项目重构而来。

## 项目结构

```
.
├── app/
│   ├── main.py              # FastAPI入口文件
│   ├── api/
│   │   ├── __init__.py      # API路由注册
│   │   ├── deps.py          # 依赖注入（认证、数据库会话等）
│   │   └── v1/
│   │       ├── auth.py      # 认证API
│   │       ├── chat.py      # 聊天API
│   │       ├── documents.py # 文档管理API
│   │       ├── tenants.py   # 租户管理API
│   │       ├── logs.py      # 日志管理API
│   │       ├── tools.py     # 工具管理API
│   │       ├── mcp.py       # MCP服务器管理API
│   │       ├── dashboard.py # 仪表盘API
│   │       ├── monitor.py   # 系统监控API
│   │       └── health.py    # 健康检查API
│   ├── core/
│   │   ├── config.py        # 配置管理
│   │   ├── database.py      # 数据库连接
│   │   ├── redis.py         # Redis连接
│   │   ├── security.py      # 安全工具（JWT、密码）
│   │   └── exceptions.py    # 异常处理
│   ├── models/              # SQLAlchemy模型
│   ├── schemas/             # Pydantic schemas
│   └── utils/               # 工具函数
├── data/                    # 数据目录（SQLite数据库、向量存储等）
├── db/                      # 数据库文件目录
├── upload/                  # 文件上传目录
├── pyproject.toml           # 项目依赖配置
└── README.md
```

## 技术栈

- **框架**: FastAPI
- **数据库**: SQLAlchemy (支持 PostgreSQL / SQLite)
- **缓存**: Redis
- **认证**: JWT (python-jose)
- **向量存储**: Chroma / Qdrant / Milvus
- **LLM**: LangChain + OpenAI
- **异步任务**: Celery

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

或使用uv:

```bash
uv pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件（可选，使用默认配置也可运行）:

```env
# 应用配置
APP_ENV=dev
APP_PORT=8000
DEBUG=true

# 数据库（默认使用SQLite）
USE_SQLITE=true
SQLITE_DSN=sqlite+aiosqlite:///./data/app.db

# 如需使用PostgreSQL
# USE_SQLITE=false
# POSTGRES_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_assistant

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o-mini
EMBEDDING_MODEL_NAME=text-embedding-3-small

# 向量存储
VECTOR_STORE_PROVIDER=chroma
CHROMA_PERSIST_DIR=./data/chroma

# 文件上传
UPLOAD_DIR=./data/uploads
MAX_UPLOAD_SIZE_MB=20
```

### 3. 启动服务

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/api/v1/health

### 5. 默认用户

系统启动时会自动创建默认管理员用户：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | super_admin |

**注意**: 生产环境请务必修改默认密码！

## API端点

### 认证 `/api/v1/auth`
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /login | 登录 |
| POST | /logout | 登出 |
| POST | /refresh | 刷新Token |
| GET | /me | 获取当前用户信息 |

### 聊天 `/api/v1/chat`
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /sessions | 创建会话 |
| GET | /sessions | 获取会话列表 |
| GET | /sessions/{sessionId} | 获取会话详情 |
| PATCH | /sessions/{sessionId} | 更新会话 |
| DELETE | /sessions/{sessionId} | 删除会话 |
| POST | /messages | 发送消息 |
| GET | /messages | 获取消息列表 |
| DELETE | /messages/{messageId} | 删除消息 |
| GET | /prompts | 获取提示标签 |
| GET | /suggestions | 获取建议问题 |

### 文档 `/api/v1/documents`
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /upload | 上传文档 |
| GET | / | 获取文档列表 |
| GET | /{documentId} | 获取文档详情 |
| DELETE | /{documentId} | 删除文档 |
| POST | /{documentId}/retry | 重试处理失败的文档 |
| GET | /{documentId}/chunks | 获取文档分块列表 |

### 租户管理 `/api/v1/admin/tenants`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | / | 获取租户列表 |
| POST | / | 创建租户 |
| GET | /{tenantId} | 获取租户详情 |
| PATCH | /{tenantId} | 更新租户 |
| DELETE | /{tenantId} | 删除租户 |

### 日志管理 `/api/v1/admin/logs`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /audit | 获取审计日志 |
| GET | /qa | 获取QA日志 |
| GET | /qa/{logId} | 获取QA日志详情 |
| GET | /tools | 获取工具调用日志 |
| GET | /tools/{logId} | 获取工具调用日志详情 |
| GET | /export | 导出日志 |

### 工具管理 `/api/v1/admin/tools`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | / | 获取工具列表 |
| POST | / | 创建工具 |
| GET | /{toolId} | 获取工具详情 |
| PATCH | /{toolId} | 更新工具 |
| DELETE | /{toolId} | 删除工具 |

### MCP服务器 `/api/v1/admin/mcp`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /servers | 获取MCP服务器列表 |
| POST | /servers | 创建MCP服务器 |
| GET | /servers/{serverId} | 获取服务器详情 |
| PATCH | /servers/{serverId} | 更新服务器 |
| DELETE | /servers/{serverId} | 删除服务器 |
| POST | /servers/{serverId}/connect | 连接服务器 |
| POST | /servers/{serverId}/disconnect | 断开服务器 |
| GET | /tools | 获取MCP工具列表 |

### 仪表盘 `/api/v1/admin/dashboard`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /overview | 获取概览统计 |
| GET | /trends | 获取趋势数据 |
| GET | /rankings | 获取排名数据 |

### 系统监控 `/api/v1/admin/monitor`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /online-users | 获取在线用户数 |
| GET | /traffic | 获取流量统计 |
| GET | /tokens | 获取Token使用统计 |
| GET | /errors | 获取错误统计 |
| GET | /response-time | 获取响应时间统计 |

### 健康检查 `/api/v1/health`
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | / | 基础健康检查 |
| GET | /db | 数据库健康检查 |
| GET | /redis | Redis健康检查 |
| GET | /all | 全部服务健康检查 |

### 公开接口 `/api/v1/public`
无需认证，可对外提供给第三方平台或机器人使用。

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /precise | 精准回答接口（流式） |
| POST | /chat | 公开聊天接口（流式） |
| POST | /search | 知识库搜索接口（Legacy） |

#### `/public/precise` - 精准回答接口

用于机器人/第三方平台调用，返回精确答案。

**特点**：
- 流式输出（SSE），只返回精确答案
- 默认只搜索公开知识库
- 无结果时返回友好提示 + 客服电话

**请求参数**：
```json
{
  "query": "你们公司叫什么",
  "tenantId": "default",       // 可选，租户ID，默认为 'default'
  "includePrivate": false      // 可选，是否包含私有库，默认 false
}
```

**流式响应**（SSE格式）：
```
data: {"event": "token", "data": {"content": "我们"}}
data: {"event": "token", "data": {"content": "公司"}}
data: {"event": "token", "data": {"content": "叫迅达物流..."}}
data: {"event": "done", "data": {"content": "完整回答", "sources": [...]}
```

**无结果时**：
```
data: {"event": "done", "data": {"content": "抱歉，这个问题我暂时无法回答，您可以联系我们的专员为您解答，客服热线：400-882-6688", "sources": []}}
```

#### `/public/chat` - 公开聊天接口

用于嵌入其他平台的聊天功能，提供完整的聊天体验。

**特点**：
- 流式输出（SSE），完整的聊天体验
- 支持多轮对话（通过 sessionId）
- 默认只搜索公开知识库
- 复用系统内部聊天逻辑

**请求参数**：
```json
{
  "query": "你们公司叫什么",
  "tenantId": "default",       // 可选，租户ID，默认为 'default'
  "sessionId": "xxx",          // 可选，会话ID，用于多轮对话
  "includePrivate": false      // 可选，是否包含私有库，默认 false
}
```

**流式响应**（SSE格式）：
```
data: {"event": "start", "data": {"messageId": "xxx"}}
data: {"event": "token", "data": {"content": "我们"}}
data: {"event": "token", "data": {"content": "公司"}}
data: {"event": "done", "data": {"messageId": "xxx", "tokenUsage": {...}, "sources": [...]}}
```

## 响应格式

所有API响应格式统一为：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

分页响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ... ],
    "total": 100,
    "pageNum": 1,
    "pageSize": 20
  }
}
```

错误响应：

```json
{
  "code": 40001,
  "message": "错误描述",
  "data": null
}
```

## 前端对接

前端需要修改API基础URL配置，指向此后端服务：

```typescript
// 前端配置示例
const API_BASE_URL = 'http://localhost:8000/api/v1';

// 请求示例
const response = await fetch(`${API_BASE_URL}/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
});
const { code, message, data } = await response.json();
```

## 数据库模型

### 核心表
- `users` - 用户表
- `tenants` - 租户表
- `chat_sessions` - 聊天会话表
- `chat_messages` - 聊天消息表
- `documents` - 文档表
- `document_chunks` - 文档分块表
- `qa_logs` - QA日志表
- `audit_logs` - 审计日志表
- `tool_call_logs` - 工具调用日志表
- `tool_definitions` - 工具定义表
- `mcp_servers` - MCP服务器表
- `mcp_tools` - MCP工具表

## 开发说明

### 添加新的API端点

1. 在 `app/api/v1/` 下创建新的路由文件
2. 在 `app/api/__init__.py` 中导入并注册路由
3. 在 `app/schemas/` 中定义请求/响应模型
4. 在 `app/models/` 中定义数据库模型（如需要）

### 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head
```

## License

MIT