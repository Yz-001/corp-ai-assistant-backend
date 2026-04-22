# AI企业助手项目（后端）开发说明书

**文档类型：AI编码执行版**
**适用对象：AI代码生成 / 后端开发 / 架构实现 / 接口实现**
**技术路线：Python 3.11 + FastAPI + PostgreSQL + Redis + Celery + 向量库适配层 + MCP 工具接入**
**当前版本：v2.0**

---

# 1. 项目概述

## 1.1 项目名称

AI企业助手（AI Enterprise Assistant）

## 1.2 项目定位

本项目是一个面向企业内部销售、外部客户、以及后续加盟商/租户接入的智能服务平台后端。
核心目标不是只做一个简单问答接口，而是构建一个可持续演进的 **企业级 AI 服务中台后端**，支撑以下场景：

1. 企业内部销售通过聊天界面快速获取产品知识、话术、培训资料
2. 官网外部客户通过聊天组件自助查询产品信息、使用说明、常见问题
3. 管理员通过后台管理租户、文档、日志、工具、MCP 服务
4. 系统具备在线人数、流量、Tokens 消耗、调用趋势等监控能力
5. 后续可扩展到订单查询、物流轨迹、CRM、售后等业务工具调用

---

# 2. 后端建设目标

本期后端需支撑两类前端：

## 2.1 用户工作台前端

对应能力包括：

* 登录与身份识别
* 左侧历史会话列表
* 新建会话
* 当前会话消息流
* 提示词 / 推荐问题
* 流式回答
* 引用来源展示
* 会话切换、删除、重命名
* 多端访问（PC / H5）

## 2.2 管理后台前端

对应能力包括：

* 管理员权限控制
* 仪表盘统计
* 租户管理
* 文档上传与管理
* 日志管理
* 工具管理
* MCP 服务管理
* 在线人数 / 流量 / Tokens / 调用趋势监控

---

# 3. 本期后端范围

## 3.1 本期必须实现

1. FastAPI 单体模块化后端
2. JWT 登录鉴权
3. 多角色与多租户权限控制
4. 会话与消息管理
5. RAG 问答服务
6. 文档上传、解析、切块、向量化、检索
7. 提示词 / 推荐问题配置与下发
8. 流式问答接口
9. 日志记录与查询
10. 工具注册与租户工具权限
11. MCP 服务接入管理
12. 监控统计接口
13. 在线人数 / 请求量 / Token 消耗统计
14. 管理后台所需分页、筛选、详情接口
15. Redis + Celery 异步任务处理

## 3.2 本期不强制实现

1. 微服务拆分
2. 复杂工作流编排
3. 多模型智能路由
4. 分布式大规模向量集群
5. 完整 BI 平台
6. 复杂审批流
7. 多活部署

---

# 4. 技术架构原则

## 4.1 总体原则

* **先单体模块化，再平滑演进**
* **先满足产品主链路，再考虑平台化**
* **业务强相关的数据必须多租户隔离**
* **AI 能力、工具能力、监控能力都必须模块化**
* **接口设计必须优先服务前端页面形态**
* **长耗时操作必须异步任务化**
* **向量库、模型服务、工具服务都必须可替换**

## 4.2 架构形态

采用 **单体模块化 + 异步任务 Worker + 外部可插拔工具/MCP** 形态：

* 主应用：FastAPI
* 关系数据库：PostgreSQL
* 缓存 / 会话 / 指标中转：Redis
* 异步任务：Celery
* 文件存储：本地开发目录 / MinIO / S3
* 向量库：首期可用 Chroma，必须抽象适配层，后续可替换 Qdrant / Milvus
* LLM / Embedding：通过统一 Provider 层封装
* MCP 接入：通过独立模块管理服务器配置与工具发现
* 监控：Prometheus 指标 + 应用内统计接口

---

# 5. 用户角色与权限模型

## 5.1 角色定义

后端必须支持以下角色：

* `super_admin`：平台超级管理员
* `tenant_admin`：租户管理员
* `tenant_user`：普通租户用户
* `public_user`：外部匿名/轻用户

## 5.2 权限规则

### `public_user`

可访问：

* 公共问答接口
* 官网聊天组件接口
* 公共提示词 / 推荐问题

不可访问：

* 私有文档
* 管理后台
* 工具调用（除明确开放工具）

### `tenant_user`

可访问：

* 聊天工作台
* 自己的历史会话
* 当前租户授权范围内的知识问答
* 当前租户授权范围内的工具能力

### `tenant_admin`

可访问：

* 租户内聊天与会话
* 租户内文档管理
* 租户内日志查看
* 租户内工具权限查看与配置
* 租户内统计看板

### `super_admin`

可访问全部：

* 全局租户管理
* 全局文档管理
* 全局日志
* 全局工具管理
* MCP 服务管理
* 在线监控与系统看板

---

# 6. 多租户模型

## 6.1 租户类型

* `public`：公共租户
* `sales`：内部销售租户
* `partner`：加盟商租户
* `enterprise`：企业客户租户

## 6.2 多租户隔离要求

所有业务主表必须显式携带 `tenant_id`，包括：

* users
* chat_sessions
* chat_messages
* documents
* document_chunks
* qa_logs
* tool_logs
* tenant_tool_permissions
* prompt_configs
* dashboard_snapshots（如有）
* usage_records

## 6.3 检索隔离规则

* 公共用户：仅可检索公共知识库
* 租户用户：可检索当前租户私有知识库 + 公共知识库
* 跨租户访问必须禁止
* 禁止仅根据前端传入 tenant_id 决定数据范围，必须由 token / 服务端上下文解析

---

# 7. 前端驱动下的核心后端能力映射

这部分是本次重写的关键：后端必须围绕前端页面能力设计。

## 7.1 聊天页对应后端能力

前端需要：

* 左侧历史会话列表
* 新建会话
* 当前会话消息流
* 输入框上方提示词、推荐问题
* 流式回复
* 引用来源
* 消息级工具调用状态
* H5 端可用

后端必须提供：

1. 会话列表接口
2. 新建/删除/重命名会话接口
3. 消息历史读取接口
4. 发送消息接口
5. SSE/流式接口
6. 推荐提示词接口
7. 推荐问题接口
8. 来源引用结构化返回
9. 工具调用记录结构化返回

## 7.2 管理后台对应后端能力

前端需要：

* 仪表盘
* 租户管理
* 文档上传与管理
* 日志管理
* 工具管理
* MCP 管理
* 实时监控

后端必须提供：

1. 仪表盘聚合接口
2. 在线人数、请求量、Tokens 趋势接口
3. 租户 CRUD
4. 文档上传/列表/详情/删除/重试解析
5. 日志列表/详情/导出
6. 工具列表/启停/授权
7. MCP 服务配置/测试连接/工具发现
8. 管理员权限校验

---

# 8. 技术栈

## 8.1 后端技术选型

* Python 3.11+
* FastAPI
* Uvicorn / Gunicorn
* SQLAlchemy 2.x
* Alembic
* Pydantic v2
* PostgreSQL
* Redis
* Celery
* httpx
* structlog 或 loguru
* Prometheus Client
* LangChain（可选，用于首期 RAG 组装）
* MCP Client / 自定义 MCP 适配模块

## 8.2 首期推荐实现

* Chroma 用于验证知识库主链路
* Redis 用于：

  * 缓存
  * 会话状态
  * 限流
  * 在线状态
  * SSE 辅助消息总线
* Celery 用于：

  * 文档解析
  * 文档重建索引
  * 统计聚合
  * 监控快照
  * 工具健康检查

## 8.3 必须预留替换能力

* 向量库适配层
* LLM Provider 适配层
* Embedding Provider 适配层
* MCP Tool Provider 适配层

---

# 9. 后端模块划分

建议按领域拆分为以下模块：

1. `auth`：登录鉴权、Token、用户上下文
2. `rbac`：角色权限、资源授权
3. `tenant`：租户管理、租户配置、配额
4. `chat`：会话、消息、流式问答
5. `prompt`：提示词、推荐问题管理
6. `knowledge`：文档、切块、索引、检索
7. `rag`：检索与生成主链路
8. `tooling`：工具注册、租户工具权限、工具调用
9. `mcp`：MCP 服务配置、连接测试、工具发现
10. `logging`：问答日志、调用日志、审计日志
11. `monitor`：在线人数、流量、tokens、趋势统计
12. `integration`：官网聊天组件、企微、开放接入
13. `tasks`：异步任务
14. `system`：健康检查、配置、metrics

---

# 10. 推荐项目目录结构

```text
app/
├─ main.py
├─ core/
│  ├─ config.py
│  ├─ security.py
│  ├─ database.py
│  ├─ redis.py
│  ├─ logger.py
│  ├─ metrics.py
│  ├─ context.py
│  ├─ exceptions.py
│  └─ constants.py
├─ api/
│  ├─ deps.py
│  ├─ router.py
│  └─ v1/
│     ├─ auth.py
│     ├─ chat.py
│     ├─ sessions.py
│     ├─ prompts.py
│     ├─ documents.py
│     ├─ tenants.py
│     ├─ logs.py
│     ├─ tools.py
│     ├─ mcp.py
│     ├─ dashboard.py
│     ├─ monitor.py
│     ├─ integrations.py
│     └─ health.py
├─ modules/
│  ├─ auth/
│  ├─ rbac/
│  ├─ tenant/
│  ├─ chat/
│  ├─ prompt/
│  ├─ knowledge/
│  ├─ rag/
│  ├─ tooling/
│  ├─ mcp/
│  ├─ logging/
│  ├─ monitor/
│  └─ integration/
├─ adapters/
│  ├─ llm/
│  ├─ embedding/
│  ├─ vector_store/
│  ├─ object_storage/
│  └─ mcp/
├─ tasks/
│  ├─ worker.py
│  ├─ document_tasks.py
│  ├─ monitor_tasks.py
│  ├─ mcp_tasks.py
│  └─ usage_tasks.py
├─ db/
│  ├─ base.py
│  ├─ models/
│  └─ migrations/
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
└─ scripts/
   ├─ seed_demo_data.py
   ├─ rebuild_vectors.py
   ├─ recalc_usage.py
   └─ init_super_admin.py
```

---

# 11. 核心业务能力设计

# 11.1 聊天与会话管理

## 会话能力

后端必须支持：

* 新建会话
* 获取历史会话列表
* 获取会话详情
* 会话重命名
* 会话删除
* 会话归档（可选）
* 多端读取同一会话历史

## 消息能力

后端必须支持：

* 发送用户消息
* 生成 AI 消息
* 流式消息输出
* 工具消息插入
* 来源引用记录
* 消息级状态（generating / done / failed）

## 推荐提示能力

为适配前端输入框上方内容，必须支持：

* 提示词标签列表
* 推荐问题列表
* 按角色/租户/场景返回
* 可后台配置
* 可按频道区分（web / public_widget / wecom）

---

# 11.2 知识库与文档管理

## 文档能力

必须支持：

* 上传 PDF / DOCX / TXT / MD
* 记录文档元数据
* 异步解析
* 状态流转：

  * pending
  * processing
  * completed
  * failed
* 文档删除
* 重试解析
* 文档重建索引
* 按租户 / 状态 / 时间筛选

## 文档解析流程

1. 上传文件
2. 校验类型和大小
3. 存储原始文件
4. 写入 documents 表
5. 投递解析任务
6. 解析文本
7. 切块
8. 生成 embedding
9. 写入向量库
10. 更新状态和统计字段

## 引用来源

RAG 回答必须返回结构化来源，供前端展示：

* document_id
* document_name
* chunk_id
* chunk_index
* snippet
* score

---

# 11.3 工具管理与工具调用

## 工具管理目标

后端需支持平台级工具管理与租户级工具授权。

## 工具能力

* 工具注册
* 工具启停
* 工具分类
* 工具配置
* 工具健康状态
* 工具调用日志
* 租户授权范围控制

## 工具类型

* `internal_api`
* `database_query`
* `http_service`
* `mcp_tool`

## 示例工具

* 订单查询
* 物流轨迹查询
* CRM 查询
* 售后工单查询
* 外部知识库检索
* MCP 工具

---

# 11.4 MCP 服务管理

这部分是新版本必须补齐的重点。

## MCP 管理目标

让管理员可管理多个 MCP 服务，并可把发现到的工具分配给不同租户使用。

## 必须支持能力

* MCP 服务列表
* 新增 MCP 服务
* 编辑配置
* 启用/停用服务
* 测试连接
* 发现工具列表
* 同步工具到平台
* 租户绑定可用工具
* 工具健康检查

## MCP 服务配置项

* 名称
* 服务地址
* 协议类型
* 鉴权类型
* token / secret
* 描述
* 状态
* 超时时间
* 最近检查时间
* 最近检查结果

---

# 11.5 仪表盘与监控能力

为支撑前端“当前多少人登录使用、流量、tokens 监测”，后端必须具备统计与实时查询能力。

## 必须支持统计维度

* 当前在线人数
* 今日活跃用户数
* 今日问答次数
* 今日请求数
* 今日文档上传数
* 今日工具调用次数
* 今日 Token 消耗
* 今日错误数
* 平均响应耗时
* 租户使用排行
* 工具调用排行

## 趋势图能力

至少提供以下趋势数据：

* 最近 7 天问答次数
* 最近 7 天 Token 消耗
* 最近 7 天请求量
* 最近 7 天错误率
* 在线人数实时趋势
* 接口响应时间趋势

## 在线人数实现建议

采用以下方式之一：

1. WebSocket / SSE 心跳 + Redis 过期键
2. 每次请求刷新在线状态 TTL
3. 定时聚合活跃用户数

建议定义：

* 5 分钟内活跃 = 在线
* 30 分钟内活跃 = 活跃用户

---

# 12. 核心数据模型设计

下面给的是后端重点表设计方向。

## 12.1 users

```text
id
tenant_id
username
email
password_hash
role
status
last_login_at
created_at
updated_at
```

## 12.2 tenants

```text
id
name
code
type
status
plan_type
quota_json
config_json
created_at
updated_at
```

## 12.3 chat_sessions

```text
id
tenant_id
user_id
title
channel
status
last_message_at
created_at
updated_at
```

## 12.4 chat_messages

```text
id
tenant_id
session_id
role              # user / assistant / system / tool
content
status            # pending / generating / done / failed
sources_json
tool_calls_json
token_usage_json
created_at
updated_at
```

## 12.5 prompt_configs

```text
id
tenant_id
scope             # global / tenant / channel
channel           # web / public_widget / wecom
type              # tag / suggested_question
title
content
sort_order
enabled
created_at
updated_at
```

## 12.6 documents

```text
id
tenant_id
name
file_name
file_type
file_size
storage_path
visibility        # public / private
status            # pending / processing / completed / failed
chunk_count
created_by
error_message
created_at
updated_at
```

## 12.7 document_chunks

```text
id
tenant_id
document_id
chunk_index
content
token_count
metadata_json
created_at
updated_at
```

## 12.8 qa_logs

```text
id
tenant_id
user_id
session_id
query
answer
model_name
latency_ms
prompt_tokens
completion_tokens
total_tokens
source_count
status
error_message
created_at
```

## 12.9 tool_definitions

```text
id
code
name
type
description
status
config_json
health_status
created_at
updated_at
```

## 12.10 tenant_tool_permissions

```text
id
tenant_id
tool_id
enabled
config_json
created_at
updated_at
```

## 12.11 tool_call_logs

```text
id
tenant_id
session_id
message_id
tool_id
tool_name
request_json
response_json
latency_ms
status
error_message
created_at
```

## 12.12 mcp_servers

```text
id
name
base_url
auth_type
auth_config_json
status
timeout_seconds
description
last_check_at
last_check_status
created_at
updated_at
```

## 12.13 mcp_tools

```text
id
server_id
tool_code
tool_name
description
schema_json
status
created_at
updated_at
```

## 12.14 usage_records

```text
id
tenant_id
user_id
service_type
request_count
token_count
cost
stat_date
created_at
```

## 12.15 audit_logs

```text
id
tenant_id
operator_id
module
action
target_type
target_id
detail_json
created_at
```

---

# 13. 向量库设计

## 13.1 首期方案

首期使用 Chroma 或 Qdrant 均可，但代码层必须通过 `VectorStoreAdapter` 封装。

## 13.2 collection 命名建议

* `kb_public`
* `kb_tenant_{tenant_id}`

## 13.3 metadata 必须包含

* tenant_id
* document_id
* document_name
* visibility
* chunk_index
* source_type

## 13.4 检索规则

* 公共用户查公共库
* 租户用户查公共库 + 当前租户私有库
* 合并结果后返回 top_k
* 后续可增加 rerank 能力

---

# 14. API 设计规范

## 14.1 统一前缀

```text
/api/v1
```

## 14.2 统一响应格式

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败：

```json
{
  "code": 4001,
  "message": "invalid parameter",
  "data": null
}
```

## 14.3 分页参数规范

统一使用：

* `pageNum`
* `pageSize`

统一返回：

* `list`
* `total`
* `pageNum`
* `pageSize`

---

# 15. 接口清单设计

# 15.1 认证接口

* `POST /api/v1/auth/login`
* `POST /api/v1/auth/refresh`
* `GET /api/v1/auth/me`
* `POST /api/v1/auth/logout`

# 15.2 聊天与会话接口

* `POST /api/v1/chat/sessions`
* `GET /api/v1/chat/sessions`
* `GET /api/v1/chat/sessions/{sessionId}`
* `PATCH /api/v1/chat/sessions/{sessionId}`
* `DELETE /api/v1/chat/sessions/{sessionId}`
* `POST /api/v1/chat/messages`
* `POST /api/v1/chat/messages/stream`
* `POST /api/v1/chat/messages/{messageId}/stop`
* `GET /api/v1/chat/prompts`
* `GET /api/v1/chat/suggestions`

# 15.3 文档管理接口

* `POST /api/v1/documents/upload`
* `GET /api/v1/documents`
* `GET /api/v1/documents/{documentId}`
* `DELETE /api/v1/documents/{documentId}`
* `POST /api/v1/documents/{documentId}/reindex`
* `POST /api/v1/documents/{documentId}/retry`
* `GET /api/v1/documents/{documentId}/chunks`

# 15.4 租户管理接口

* `GET /api/v1/admin/tenants`
* `POST /api/v1/admin/tenants`
* `GET /api/v1/admin/tenants/{tenantId}`
* `PUT /api/v1/admin/tenants/{tenantId}`
* `PATCH /api/v1/admin/tenants/{tenantId}/status`
* `GET /api/v1/admin/tenants/{tenantId}/usage`
* `GET /api/v1/admin/tenants/{tenantId}/tools`

# 15.5 日志接口

* `GET /api/v1/admin/logs/qa`
* `GET /api/v1/admin/logs/qa/{logId}`
* `GET /api/v1/admin/logs/tools`
* `GET /api/v1/admin/logs/tools/{logId}`
* `GET /api/v1/admin/logs/audit`
* `GET /api/v1/admin/logs/export`

# 15.6 工具管理接口

* `GET /api/v1/admin/tools`
* `POST /api/v1/admin/tools`
* `PUT /api/v1/admin/tools/{toolId}`
* `PATCH /api/v1/admin/tools/{toolId}/status`
* `GET /api/v1/admin/tools/{toolId}/stats`
* `PUT /api/v1/admin/tenants/{tenantId}/tools/{toolId}`

# 15.7 MCP 管理接口

* `GET /api/v1/admin/mcp/servers`
* `POST /api/v1/admin/mcp/servers`
* `GET /api/v1/admin/mcp/servers/{serverId}`
* `PUT /api/v1/admin/mcp/servers/{serverId}`
* `PATCH /api/v1/admin/mcp/servers/{serverId}/status`
* `POST /api/v1/admin/mcp/servers/{serverId}/test`
* `POST /api/v1/admin/mcp/servers/{serverId}/discover-tools`
* `GET /api/v1/admin/mcp/tools`
* `PUT /api/v1/admin/mcp/tools/{toolId}/bind-tenants`

# 15.8 仪表盘与监控接口

* `GET /api/v1/admin/dashboard/overview`
* `GET /api/v1/admin/dashboard/trends`
* `GET /api/v1/admin/dashboard/rankings`
* `GET /api/v1/admin/monitor/online-users`
* `GET /api/v1/admin/monitor/traffic`
* `GET /api/v1/admin/monitor/tokens`
* `GET /api/v1/admin/monitor/errors`
* `GET /api/v1/admin/monitor/response-time`

# 15.9 集成接口

* `POST /api/v1/integrations/public/chat`
* `POST /api/v1/integrations/wecom/callback`

# 15.10 系统接口

* `GET /api/v1/health`
* `GET /api/v1/metrics`

---

# 16. 关键接口结构示例

## 16.1 新建会话

`POST /api/v1/chat/sessions`

请求：

```json
{
  "title": "新会话",
  "channel": "web"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "sessionId": "xxx",
    "title": "新会话"
  }
}
```

## 16.2 获取提示词

`GET /api/v1/chat/prompts`

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "tags": [
      "产品知识",
      "销售话术",
      "使用教程",
      "订单查询"
    ],
    "suggestions": [
      "这款产品适合哪些客户？",
      "新员工怎么快速了解产品？",
      "客户问价格高怎么回答？"
    ]
  }
}
```

## 16.3 发送消息

`POST /api/v1/chat/messages`

请求：

```json
{
  "sessionId": "xxx",
  "query": "这款产品适合哪些客户？",
  "channel": "web"
}
```

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "messageId": "msg_xxx",
    "answer": "该产品适合……",
    "sources": [
      {
        "documentId": "doc_1",
        "documentName": "销售手册.pdf",
        "chunkId": "chunk_12",
        "snippet": "……"
      }
    ],
    "toolCalls": [],
    "tokenUsage": {
      "promptTokens": 320,
      "completionTokens": 180,
      "totalTokens": 500
    }
  }
}
```

## 16.4 仪表盘总览

`GET /api/v1/admin/dashboard/overview`

响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "onlineUsers": 126,
    "todayActiveUsers": 893,
    "todayQaCount": 12560,
    "todayRequestCount": 18733,
    "todayTokenCount": 2839001,
    "todayUploadCount": 48,
    "todayToolCalls": 902,
    "errorRate": 0.012,
    "avgLatencyMs": 1245
  }
}
```

---

# 17. 核心业务流程

# 17.1 聊天流程

1. 用户进入聊天页，拉取历史会话列表
2. 用户新建会话或进入既有会话
3. 前端拉取提示词/推荐问题
4. 用户发送消息
5. 服务端解析用户上下文、tenant_id、role、channel
6. 判断是否需要工具调用
7. 先做知识检索，再决定是否调用工具
8. 生成回答
9. 返回结构化 sources / toolCalls / tokenUsage
10. 写入 chat_messages、qa_logs、usage_records

# 17.2 文档上传流程

1. 管理员上传文档
2. 写 documents 表
3. 投递 Celery 任务
4. 解析、切块、embedding、入向量库
5. 更新状态
6. 后台列表页可看到状态流转

# 17.3 MCP 接入流程

1. 管理员创建 MCP Server
2. 系统测试连接
3. 发现工具列表
4. 同步工具定义
5. 绑定租户权限
6. 聊天场景下按租户可见工具执行

# 17.4 监控统计流程

1. 每次请求记录计数与耗时
2. 每次 LLM 调用记录 tokens
3. 每次工具调用记录结果
4. Redis 维护在线用户 TTL
5. 定时任务汇总 usage_records 与 monitor 快照
6. 仪表盘接口返回聚合结果

---

# 18. 安全设计

## 18.1 鉴权要求

* 内部用户接口：JWT
* 管理后台：JWT + 角色校验
* 公开聊天：匿名 session + 限流
* 企微回调：签名校验

## 18.2 数据安全

* 所有查询强制 tenant_id 过滤
* 上传文件校验文件类型和大小
* 配置密钥使用环境变量
* 不允许前端直接决定权限范围
* 敏感日志脱敏

## 18.3 限流策略

* 公共聊天接口按 IP / session 限流
* 租户接口按 tenant_id 限流
* 工具调用按工具级别限流
* MCP 服务调用按 server 级别限流

---

# 19. 监控与可观测性

## 19.1 日志要求

必须记录：

1. API 请求日志
2. 聊天日志
3. 模型调用日志
4. 工具调用日志
5. MCP 调用日志
6. 文档解析日志
7. 审计日志
8. 错误日志

## 19.2 指标要求

Prometheus 至少暴露：

* 请求总数
* 请求耗时
* SSE 活跃连接数
* 在线用户估算值
* 聊天成功率
* 文档解析成功率
* 工具调用成功率
* LLM tokens 总量
* 平均响应时间
* 错误率

## 19.3 Trace 建议

后续接入：

* LangSmith
* OpenTelemetry

链路建议追踪：

* 用户提问
* 检索结果
* Prompt
* 模型返回
* 工具调用
* 最终响应

---

# 20. 配置设计

建议 `.env`：

```env
APP_NAME=ai-enterprise-assistant
APP_ENV=dev
APP_PORT=8000

POSTGRES_DSN=postgresql://user:pass@localhost:5432/ai_assistant
REDIS_URL=redis://localhost:6379/0

JWT_SECRET=your_secret
JWT_EXPIRE_MINUTES=10080

OPENAI_API_KEY=
OPENAI_BASE_URL=
LLM_MODEL_NAME=
EMBEDDING_MODEL_NAME=

VECTOR_STORE_PROVIDER=chroma
CHROMA_PERSIST_DIR=./data/chroma

OBJECT_STORAGE_PROVIDER=local
UPLOAD_DIR=./data/uploads

MAX_UPLOAD_SIZE_MB=20
DEFAULT_TOP_K=5
CHAT_TIMEOUT_SECONDS=60
TOOL_TIMEOUT_SECONDS=15
MCP_TIMEOUT_SECONDS=20
ONLINE_USER_TTL_SECONDS=300
ACTIVE_USER_TTL_SECONDS=1800
```

---

# 21. 开发规范

## 21.1 编码规范

* 必须使用类型注解
* 必须分层：router / service / repository / model / schema
* 不允许在路由层写复杂业务逻辑
* 不允许业务模块直接耦合具体向量库实现
* 所有接口必须有 request / response schema
* 所有异常统一处理

## 21.2 测试要求

至少包含：

* 单元测试
* API 集成测试
* 多租户隔离测试
* 文档上传链路测试
* 问答链路测试
* 工具调用权限测试
* MCP 服务连接测试
* 仪表盘统计接口测试

---

# 22. 实施阶段建议

## Phase 1：后端基础骨架

* FastAPI 项目骨架
* JWT 登录
* 用户/租户模型
* 聊天主接口
* 会话与消息存储

## Phase 2：知识库与文档管理

* 文档上传
* 解析与向量化
* 文档管理接口
* RAG 主链路

## Phase 3：管理员后台支撑

* 仪表盘总览接口
* 租户管理
* 日志管理
* 文档列表管理

## Phase 4：工具与 MCP

* 工具注册
* 租户工具授权
* MCP 服务管理
* 工具调用日志

## Phase 5：监控与运维能力

* 在线人数
* 请求量 / Tokens 统计
* 趋势接口
* 健康检查与 metrics

---

# 23. AI 实现约束（给 AI 编码时必须遵守）

1. 必须使用 **FastAPI + PostgreSQL + Redis + Celery**
2. 必须采用 **单体模块化架构**
3. 所有核心业务表必须带 `tenant_id`
4. 所有分页接口统一使用 `pageNum / pageSize`
5. 所有 API 返回统一 JSON 结构
6. 聊天接口必须支持：

   * 历史会话
   * 新建会话
   * 消息流
   * 提示词 / 推荐问题
   * 来源引用
7. 管理后台必须支持：

   * 租户管理
   * 文档上传与管理
   * 日志管理
   * 工具管理
   * MCP 管理
   * 仪表盘与监控
8. 必须支持在线人数、流量、Tokens 的统计接口
9. 工具调用必须走可扩展注册机制
10. MCP 服务必须独立建模管理
11. 文档解析必须异步任务化
12. 向量库必须通过适配层封装
13. 配置必须来自环境变量
14. 必须提供 OpenAPI 文档
15. 必须提供基础测试用例
16. 必须提供本地启动所需：

* `requirements.txt` 或 `pyproject.toml`
* `docker-compose.yml`
* `.env.example`
* Alembic migration
* README

---

# 24. 最终交付物要求

AI 生成项目时，至少输出：

1. 完整 FastAPI 后端代码
2. 数据库模型
3. Alembic 迁移脚本
4. JWT 鉴权模块
5. 多租户上下文处理
6. 聊天与会话模块
7. 提示词 / 推荐问题模块
8. 文档上传与解析模块
9. RAG 检索与生成模块
10. 工具管理模块
11. MCP 管理模块
12. 仪表盘与监控模块
13. 日志模块
14. 向量库适配层
15. Docker Compose
16. `.env.example`
17. README
18. 基础测试用例

---

# 25. 一句话总结

这不是一个“只有 `/chat` 接口的问答后端”，而是一个**面向企业 AI 助手产品落地的完整后端基础平台**：
既要支撑**普通用户聊天体验**，也要支撑**管理员后台管理与监控**，同时还要为**工具调用、MCP 接入、多租户运营**预留清晰的扩展结构。

如果你愿意，我下一步可以直接继续给你补成这三种里最实用的一种：**《后端接口清单 + 字段级定义版》**。
