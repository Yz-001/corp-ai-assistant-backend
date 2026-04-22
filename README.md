# AI Enterprise Assistant Backend

纯后端FastAPI项目，从Next.js全栈项目重构而来。

## 项目结构

```
backend/
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
├── pyproject.toml           # 项目依赖
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -e .
```

或使用uv:

```bash
uv pip install -e .
```

### 2. 配置环境变量

创建 `.env` 文件:

```env
# 应用配置
APP_ENV=dev
APP_PORT=8000

# 数据库
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/ai_assistant

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=your-super-secret-key-change-in-production

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 启动服务

```bash
# 开发模式
python -m app.main

# 或使用uvicorn
uvicorn app.main:app --reload --port 8000
```

### 4. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API端点

### 认证
- `POST /api/v1/auth/login` - 登录
- `POST /api/v1/auth/logout` - 登出
- `POST /api/v1/auth/refresh` - 刷新Token
- `GET /api/v1/auth/me` - 获取当前用户信息

### 聊天
- `POST /api/v1/chat/sessions` - 创建会话
- `GET /api/v1/chat/sessions` - 获取会话列表
- `GET /api/v1/chat/sessions/{sessionId}` - 获取会话详情
- `PATCH /api/v1/chat/sessions/{sessionId}` - 更新会话
- `DELETE /api/v1/chat/sessions/{sessionId}` - 删除会话
- `POST /api/v1/chat/messages` - 发送消息
- `GET /api/v1/chat/prompts` - 获取提示标签
- `GET /api/v1/chat/suggestions` - 获取建议问题

### 文档
- `POST /api/v1/documents/upload` - 上传文档
- `GET /api/v1/documents` - 获取文档列表
- `GET /api/v1/documents/{documentId}` - 获取文档详情
- `DELETE /api/v1/documents/{documentId}` - 删除文档

### 管理后台
- `/api/v1/admin/tenants` - 租户管理
- `/api/v1/admin/logs` - 日志管理
- `/api/v1/admin/tools` - 工具管理
- `/api/v1/admin/mcp` - MCP服务器管理
- `/api/v1/admin/dashboard` - 仪表盘数据
- `/api/v1/admin/monitor` - 系统监控

### 健康检查
- `GET /health` - 基础健康检查
- `GET /api/v1/health/db` - 数据库健康检查
- `GET /api/v1/health/redis` - Redis健康检查
- `GET /api/v1/health/all` - 全部服务健康检查

## 前端对接

前端需要修改API基础URL配置，指向此后端服务：

```typescript
// 前端配置示例
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

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
    "list": [ ... ],
    "total": 100,
    "pageNum": 1,
    "pageSize": 20
  }
}