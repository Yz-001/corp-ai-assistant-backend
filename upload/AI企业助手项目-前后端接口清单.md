# AI企业助手项目-前后端接口清单

**文档类型：前后端联调 / AI编码执行版**
**适用对象：前端开发 / 后端开发 / AI代码生成**
**版本：v1.0**

---

# 1. 接口设计总约定

## 1.1 接口前缀

```text
/api/v1
```

## 1.2 认证方式

后台和租户内接口统一使用：

```http
Authorization: Bearer <token>
```

公开聊天组件接口可使用：

* 匿名 `sessionToken`
* 或服务端签发临时 token

---

## 1.3 统一响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

### 失败响应

```json
{
  "code": 4001,
  "message": "invalid parameter",
  "data": null
}
```

---

## 1.4 分页参数规范

所有列表接口统一：

### 请求参数

* `pageNum`
* `pageSize`

### 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "list": [],
    "total": 100,
    "pageNum": 1,
    "pageSize": 20
  }
}
```

---

## 1.5 通用状态枚举建议

### 通用启停状态

* `enabled`
* `disabled`

### 文档状态

* `pending`
* `processing`
* `completed`
* `failed`

### 会话状态

* `active`
* `archived`
* `deleted`

### 消息状态

* `pending`
* `generating`
* `done`
* `failed`
* `stopped`

### 日志状态

* `success`
* `failed`

---

# 2. 前端对接清单

这部分是给前端和 AI 用的，说明**每个页面需要依赖哪些后端接口**。

---

# 3. 登录与用户态

## 3.1 登录页

### 功能

* 用户登录
* 获取当前用户信息
* 登录后根据角色跳转页面

### 对接接口

* `POST /api/v1/auth/login`
* `GET /api/v1/auth/me`
* `POST /api/v1/auth/logout`

### 前端关键状态

* `token`
* `userInfo`
* `role`
* `tenantInfo`

---

# 4. 聊天工作台

## 4.1 聊天首页 / 当前会话页

### 页面能力

* 左侧历史会话
* 新建会话
* 当前会话消息流
* 输入框
* 提示词标签
* 推荐问题
* 流式问答
* 停止生成
* 删除会话
* 重命名会话

### 对接接口

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

### 前端展示字段

#### 会话列表

* `sessionId`
* `title`
* `lastMessageAt`
* `updatedAt`

#### 消息列表

* `messageId`
* `role`
* `content`
* `status`
* `sources`
* `toolCalls`
* `createdAt`

#### 提示词 / 推荐问题

* `tags`
* `suggestions`

---

# 5. 仪表盘页（管理员）

## 5.1 页面能力

* 指标卡片
* 趋势图
* 排行榜
* 在线人数
* 流量监控
* token 监控

### 对接接口

* `GET /api/v1/admin/dashboard/overview`
* `GET /api/v1/admin/dashboard/trends`
* `GET /api/v1/admin/dashboard/rankings`
* `GET /api/v1/admin/monitor/online-users`
* `GET /api/v1/admin/monitor/traffic`
* `GET /api/v1/admin/monitor/tokens`
* `GET /api/v1/admin/monitor/errors`
* `GET /api/v1/admin/monitor/response-time`

### 前端关键展示

* `onlineUsers`
* `todayActiveUsers`
* `todayQaCount`
* `todayTokenCount`
* `todayRequestCount`
* `avgLatencyMs`
* `errorRate`
* `trendList`
* `rankingList`

---

# 6. 租户管理页

## 6.1 页面能力

* 租户列表
* 搜索 / 筛选
* 新建租户
* 编辑租户
* 启用/禁用
* 查看租户详情
* 查看租户工具权限
* 查看租户使用量

### 对接接口

* `GET /api/v1/admin/tenants`
* `POST /api/v1/admin/tenants`
* `GET /api/v1/admin/tenants/{tenantId}`
* `PUT /api/v1/admin/tenants/{tenantId}`
* `PATCH /api/v1/admin/tenants/{tenantId}/status`
* `GET /api/v1/admin/tenants/{tenantId}/usage`
* `GET /api/v1/admin/tenants/{tenantId}/tools`
* `PUT /api/v1/admin/tenants/{tenantId}/tools/{toolId}`

### 前端关键展示

* `tenantId`
* `name`
* `code`
* `type`
* `status`
* `planType`
* `userCount`
* `documentCount`
* `requestCount`
* `tokenCount`
* `createdAt`

---

# 7. 文档上传与管理页

## 7.1 页面能力

* 上传文档
* 查看文档列表
* 状态筛选
* 删除文档
* 详情查看
* 重试解析
* 重建索引

### 对接接口

* `POST /api/v1/documents/upload`
* `GET /api/v1/documents`
* `GET /api/v1/documents/{documentId}`
* `DELETE /api/v1/documents/{documentId}`
* `POST /api/v1/documents/{documentId}/retry`
* `POST /api/v1/documents/{documentId}/reindex`
* `GET /api/v1/documents/{documentId}/chunks`

### 前端关键展示

* `documentId`
* `name`
* `fileType`
* `fileSize`
* `tenantName`
* `visibility`
* `status`
* `chunkCount`
* `createdBy`
* `createdAt`
* `errorMessage`

---

# 8. 日志管理页

## 8.1 页面能力

* 问答日志列表
* 工具调用日志列表
* 审计日志列表
* 筛选 / 搜索
* 查看详情
* 导出

### 对接接口

* `GET /api/v1/admin/logs/qa`
* `GET /api/v1/admin/logs/qa/{logId}`
* `GET /api/v1/admin/logs/tools`
* `GET /api/v1/admin/logs/tools/{logId}`
* `GET /api/v1/admin/logs/audit`
* `GET /api/v1/admin/logs/export`

### 前端关键展示

* `logId`
* `tenantName`
* `userName`
* `query`
* `answer`
* `toolName`
* `modelName`
* `latencyMs`
* `promptTokens`
* `completionTokens`
* `totalTokens`
* `status`
* `createdAt`

---

# 9. 工具管理页

## 9.1 页面能力

* 工具列表
* 工具启停
* 工具配置
* 调用统计
* 租户授权

### 对接接口

* `GET /api/v1/admin/tools`
* `POST /api/v1/admin/tools`
* `PUT /api/v1/admin/tools/{toolId}`
* `PATCH /api/v1/admin/tools/{toolId}/status`
* `GET /api/v1/admin/tools/{toolId}/stats`
* `PUT /api/v1/admin/tenants/{tenantId}/tools/{toolId}`

### 前端关键展示

* `toolId`
* `code`
* `name`
* `type`
* `status`
* `healthStatus`
* `callCount`
* `avgLatencyMs`
* `errorRate`

---

# 10. MCP 管理页

## 10.1 页面能力

* MCP 服务列表
* 新增 / 编辑服务
* 启停服务
* 测试连接
* 发现工具
* 查看工具清单
* 分配租户

### 对接接口

* `GET /api/v1/admin/mcp/servers`
* `POST /api/v1/admin/mcp/servers`
* `GET /api/v1/admin/mcp/servers/{serverId}`
* `PUT /api/v1/admin/mcp/servers/{serverId}`
* `PATCH /api/v1/admin/mcp/servers/{serverId}/status`
* `POST /api/v1/admin/mcp/servers/{serverId}/test`
* `POST /api/v1/admin/mcp/servers/{serverId}/discover-tools`
* `GET /api/v1/admin/mcp/tools`
* `PUT /api/v1/admin/mcp/tools/{toolId}/bind-tenants`

### 前端关键展示

* `serverId`
* `name`
* `baseUrl`
* `authType`
* `status`
* `timeoutSeconds`
* `lastCheckAt`
* `lastCheckStatus`
* `toolCount`

---

# 11. 系统监控页

## 11.1 页面能力

* 在线人数
* 当前请求量
* token 消耗
* 错误率
* 响应时间
* 热门租户排行
* 热门工具排行

### 对接接口

* `GET /api/v1/admin/monitor/online-users`
* `GET /api/v1/admin/monitor/traffic`
* `GET /api/v1/admin/monitor/tokens`
* `GET /api/v1/admin/monitor/errors`
* `GET /api/v1/admin/monitor/response-time`

---

# 12. 后端 API 清单

下面这部分是**真正给后端和 AI 用的 API 清单**。

---

# 13. 认证模块

## 13.1 登录

### `POST /api/v1/auth/login`

### 请求体

```json
{
  "username": "admin",
  "password": "123456"
}
```

### 响应体

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "accessToken": "xxx",
    "refreshToken": "xxx",
    "expiresIn": 7200,
    "userInfo": {
      "userId": "u_001",
      "username": "admin",
      "role": "super_admin",
      "tenantId": "t_001",
      "tenantName": "平台总部"
    }
  }
}
```

---

## 13.2 刷新 token

### `POST /api/v1/auth/refresh`

### 请求体

```json
{
  "refreshToken": "xxx"
}
```

---

## 13.3 获取当前用户

### `GET /api/v1/auth/me`

### 响应核心字段

* `userId`
* `username`
* `email`
* `role`
* `tenantId`
* `tenantName`
* `permissions`

---

## 13.4 退出登录

### `POST /api/v1/auth/logout`

---

# 14. 聊天与会话模块

## 14.1 新建会话

### `POST /api/v1/chat/sessions`

### 请求体

```json
{
  "title": "新会话",
  "channel": "web"
}
```

### 响应字段

* `sessionId`
* `title`
* `channel`
* `status`
* `createdAt`

---

## 14.2 获取会话列表

### `GET /api/v1/chat/sessions?pageNum=1&pageSize=20&keyword=报价`

### 查询参数

* `pageNum`
* `pageSize`
* `keyword` 可选

### 返回字段

* `sessionId`
* `title`
* `lastMessageAt`
* `updatedAt`

---

## 14.3 获取会话详情

### `GET /api/v1/chat/sessions/{sessionId}`

### 返回字段

```json
{
  "sessionId": "s_001",
  "title": "产品咨询",
  "channel": "web",
  "status": "active",
  "messages": [
    {
      "messageId": "m_001",
      "role": "user",
      "content": "这款产品适合哪些客户？",
      "status": "done",
      "createdAt": "2026-04-22 12:00:00"
    },
    {
      "messageId": "m_002",
      "role": "assistant",
      "content": "该产品适合...",
      "status": "done",
      "sources": [
        {
          "documentId": "d_001",
          "documentName": "销售手册.pdf",
          "chunkId": "c_001",
          "chunkIndex": 1,
          "snippet": "适合中小企业...",
          "score": 0.93
        }
      ],
      "toolCalls": [],
      "tokenUsage": {
        "promptTokens": 200,
        "completionTokens": 120,
        "totalTokens": 320
      },
      "createdAt": "2026-04-22 12:00:03"
    }
  ]
}
```

---

## 14.4 重命名会话

### `PATCH /api/v1/chat/sessions/{sessionId}`

### 请求体

```json
{
  "title": "销售报价问答"
}
```

---

## 14.5 删除会话

### `DELETE /api/v1/chat/sessions/{sessionId}`

---

## 14.6 发送消息（非流式）

### `POST /api/v1/chat/messages`

### 请求体

```json
{
  "sessionId": "s_001",
  "query": "这款产品适合哪些客户？",
  "channel": "web"
}
```

### 响应字段

* `messageId`
* `answer`
* `sources`
* `toolCalls`
* `tokenUsage`
* `latencyMs`

---

## 14.7 发送消息（流式）

### `POST /api/v1/chat/messages/stream`

### 说明

* 使用 `text/event-stream`
* 返回 SSE 事件流

### 请求体

```json
{
  "sessionId": "s_001",
  "query": "帮我总结一下售后政策",
  "channel": "web"
}
```

### SSE 事件建议

* `message_start`
* `delta`
* `tool_call`
* `sources`
* `message_end`
* `error`

---

## 14.8 停止生成

### `POST /api/v1/chat/messages/{messageId}/stop`

---

## 14.9 获取提示词标签

### `GET /api/v1/chat/prompts?channel=web`

### 返回字段

```json
{
  "tags": [
    "产品知识",
    "销售话术",
    "使用教程",
    "订单查询"
  ]
}
```

---

## 14.10 获取推荐问题

### `GET /api/v1/chat/suggestions?channel=web`

### 返回字段

```json
{
  "suggestions": [
    "这款产品适合哪些客户？",
    "新员工怎么快速了解产品？",
    "客户问价格高怎么回答？",
    "如何查询订单状态？"
  ]
}
```

---

# 15. 文档管理模块

## 15.1 上传文档

### `POST /api/v1/documents/upload`

### 请求类型

`multipart/form-data`

### 表单字段

* `file`
* `visibility`：`public | private`
* `tenantId`：超级管理员可传，普通租户管理员忽略
* `remark`：可选

### 响应字段

* `documentId`
* `status`

---

## 15.2 获取文档列表

### `GET /api/v1/documents?pageNum=1&pageSize=20&status=completed&keyword=销售`

### 查询参数

* `pageNum`
* `pageSize`
* `keyword`
* `status`
* `tenantId`
* `visibility`
* `fileType`

### 返回字段

* `documentId`
* `name`
* `fileName`
* `fileType`
* `fileSize`
* `tenantId`
* `tenantName`
* `visibility`
* `status`
* `chunkCount`
* `createdBy`
* `createdAt`
* `errorMessage`

---

## 15.3 获取文档详情

### `GET /api/v1/documents/{documentId}`

### 返回字段

* `documentId`
* `name`
* `fileName`
* `fileType`
* `fileSize`
* `storagePath`
* `tenantId`
* `tenantName`
* `visibility`
* `status`
* `chunkCount`
* `createdBy`
* `createdAt`
* `updatedAt`
* `errorMessage`

---

## 15.4 删除文档

### `DELETE /api/v1/documents/{documentId}`

---

## 15.5 重试解析

### `POST /api/v1/documents/{documentId}/retry`

---

## 15.6 重建索引

### `POST /api/v1/documents/{documentId}/reindex`

---

## 15.7 获取文档切块

### `GET /api/v1/documents/{documentId}/chunks?pageNum=1&pageSize=20`

---

# 16. 租户管理模块

## 16.1 获取租户列表

### `GET /api/v1/admin/tenants?pageNum=1&pageSize=20&keyword=华东`

### 查询参数

* `pageNum`
* `pageSize`
* `keyword`
* `status`
* `type`

### 返回字段

* `tenantId`
* `name`
* `code`
* `type`
* `status`
* `planType`
* `userCount`
* `documentCount`
* `requestCount`
* `tokenCount`
* `createdAt`

---

## 16.2 新建租户

### `POST /api/v1/admin/tenants`

### 请求体

```json
{
  "name": "华东加盟商",
  "code": "partner_east",
  "type": "partner",
  "planType": "pro",
  "status": "enabled",
  "quotaConfig": {
    "monthlyTokenLimit": 1000000,
    "dailyRequestLimit": 5000
  }
}
```

---

## 16.3 获取租户详情

### `GET /api/v1/admin/tenants/{tenantId}`

---

## 16.4 编辑租户

### `PUT /api/v1/admin/tenants/{tenantId}`

---

## 16.5 启用/禁用租户

### `PATCH /api/v1/admin/tenants/{tenantId}/status`

### 请求体

```json
{
  "status": "disabled"
}
```

---

## 16.6 获取租户使用量

### `GET /api/v1/admin/tenants/{tenantId}/usage?dateType=7d`

### 返回字段

* `requestCount`
* `tokenCount`
* `documentCount`
* `toolCallCount`
* `activeUserCount`
* `trendList`

---

## 16.7 获取租户工具权限

### `GET /api/v1/admin/tenants/{tenantId}/tools`

---

## 16.8 更新租户工具权限

### `PUT /api/v1/admin/tenants/{tenantId}/tools/{toolId}`

### 请求体

```json
{
  "enabled": true,
  "config": {
    "dailyLimit": 1000
  }
}
```

---

# 17. 日志模块

## 17.1 获取问答日志列表

### `GET /api/v1/admin/logs/qa?pageNum=1&pageSize=20`

### 查询参数

* `pageNum`
* `pageSize`
* `tenantId`
* `userId`
* `status`
* `keyword`
* `startTime`
* `endTime`

### 返回字段

* `logId`
* `tenantName`
* `userName`
* `query`
* `answer`
* `modelName`
* `latencyMs`
* `promptTokens`
* `completionTokens`
* `totalTokens`
* `status`
* `createdAt`

---

## 17.2 获取问答日志详情

### `GET /api/v1/admin/logs/qa/{logId}`

### 返回字段

* `query`
* `answer`
* `sources`
* `toolCalls`
* `latencyMs`
* `promptTokens`
* `completionTokens`
* `totalTokens`
* `errorMessage`

---

## 17.3 获取工具调用日志列表

### `GET /api/v1/admin/logs/tools?pageNum=1&pageSize=20`

---

## 17.4 获取工具调用日志详情

### `GET /api/v1/admin/logs/tools/{logId}`

---

## 17.5 获取审计日志

### `GET /api/v1/admin/logs/audit?pageNum=1&pageSize=20`

---

## 17.6 导出日志

### `GET /api/v1/admin/logs/export?type=qa&startTime=...&endTime=...`

---

# 18. 工具管理模块

## 18.1 获取工具列表

### `GET /api/v1/admin/tools?pageNum=1&pageSize=20`

### 返回字段

* `toolId`
* `code`
* `name`
* `type`
* `status`
* `healthStatus`
* `callCount`
* `avgLatencyMs`
* `errorRate`

---

## 18.2 新增工具

### `POST /api/v1/admin/tools`

### 请求体

```json
{
  "code": "order_query",
  "name": "订单查询",
  "type": "database_query",
  "description": "按订单号查询订单状态",
  "config": {
    "timeoutSeconds": 10
  }
}
```

---

## 18.3 编辑工具

### `PUT /api/v1/admin/tools/{toolId}`

---

## 18.4 启停工具

### `PATCH /api/v1/admin/tools/{toolId}/status`

### 请求体

```json
{
  "status": "enabled"
}
```

---

## 18.5 获取工具统计

### `GET /api/v1/admin/tools/{toolId}/stats?dateType=7d`

---

# 19. MCP 管理模块

## 19.1 获取 MCP 服务列表

### `GET /api/v1/admin/mcp/servers?pageNum=1&pageSize=20`

### 返回字段

* `serverId`
* `name`
* `baseUrl`
* `authType`
* `status`
* `timeoutSeconds`
* `lastCheckAt`
* `lastCheckStatus`
* `toolCount`

---

## 19.2 新增 MCP 服务

### `POST /api/v1/admin/mcp/servers`

### 请求体

```json
{
  "name": "订单系统MCP",
  "baseUrl": "https://mcp.example.com",
  "authType": "bearer",
  "authConfig": {
    "token": "xxx"
  },
  "timeoutSeconds": 20,
  "description": "订单与物流服务"
}
```

---

## 19.3 获取 MCP 服务详情

### `GET /api/v1/admin/mcp/servers/{serverId}`

---

## 19.4 编辑 MCP 服务

### `PUT /api/v1/admin/mcp/servers/{serverId}`

---

## 19.5 启停 MCP 服务

### `PATCH /api/v1/admin/mcp/servers/{serverId}/status`

---

## 19.6 测试连接

### `POST /api/v1/admin/mcp/servers/{serverId}/test`

### 返回字段

* `success`
* `message`
* `latencyMs`

---

## 19.7 发现工具

### `POST /api/v1/admin/mcp/servers/{serverId}/discover-tools`

### 返回字段

* `toolList`

  * `toolCode`
  * `toolName`
  * `description`
  * `schema`

---

## 19.8 获取 MCP 工具列表

### `GET /api/v1/admin/mcp/tools?pageNum=1&pageSize=20`

---

## 19.9 绑定租户

### `PUT /api/v1/admin/mcp/tools/{toolId}/bind-tenants`

### 请求体

```json
{
  "tenantIds": ["t_001", "t_002"]
}
```

---

# 20. 仪表盘与监控模块

## 20.1 总览

### `GET /api/v1/admin/dashboard/overview`

### 返回字段

```json
{
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
```

---

## 20.2 趋势图

### `GET /api/v1/admin/dashboard/trends?dateType=7d`

### 返回字段

* `qaTrend`
* `tokenTrend`
* `requestTrend`
* `errorTrend`
* `onlineTrend`
* `latencyTrend`

---

## 20.3 排行榜

### `GET /api/v1/admin/dashboard/rankings?dateType=7d`

### 返回字段

* `tenantRanking`
* `userRanking`
* `toolRanking`
* `hotQuestionRanking`

---

## 20.4 在线人数

### `GET /api/v1/admin/monitor/online-users`

### 返回字段

* `currentOnlineUsers`
* `trendList`

---

## 20.5 流量监控

### `GET /api/v1/admin/monitor/traffic?dateType=24h`

### 返回字段

* `requestPerMinute`
* `requestTrend`

---

## 20.6 token 监控

### `GET /api/v1/admin/monitor/tokens?dateType=24h`

### 返回字段

* `totalTokens`
* `tokensPerMinute`
* `trendList`

---

## 20.7 错误率

### `GET /api/v1/admin/monitor/errors?dateType=24h`

---

## 20.8 响应时间

### `GET /api/v1/admin/monitor/response-time?dateType=24h`

---

# 21. 公开接入模块

## 21.1 官网聊天组件

### `POST /api/v1/integrations/public/chat`

### 请求体

```json
{
  "sessionToken": "anonymous_xxx",
  "query": "这个产品怎么用？",
  "channel": "public_widget"
}
```

---

## 21.2 企业微信回调

### `POST /api/v1/integrations/wecom/callback`

### 说明

* 校验企微签名
* 转换消息格式
* 调用统一聊天链路

---

# 22. 系统模块

## 22.1 健康检查

### `GET /api/v1/health`

## 22.2 指标暴露

### `GET /api/v1/metrics`

---

# 23. 前后端联调建议

## 23.1 前端先做 mock 的模块

建议优先 mock：

* 登录
* 会话列表
* 会话详情
* 提示词 / 推荐问题
* 仪表盘 overview
* 文档列表
* 租户列表

## 23.2 后端优先开发顺序

建议顺序：

1. `auth`
2. `chat/sessions`
3. `chat/messages`
4. `chat/prompts + suggestions`
5. `documents`
6. `dashboard overview`
7. `tenants`
8. `logs`
9. `tools`
10. `mcp`
11. `monitor`

---

# 24. 给 AI 的实现要求

1. 所有列表接口统一 `pageNum/pageSize`
2. 所有接口统一响应结构
3. 所有后台接口必须带权限校验
4. 所有租户数据必须按 `tenant_id` 隔离
5. 流式接口使用 SSE
6. 文档上传必须异步解析
7. 问答接口必须返回 `sources` 和 `tokenUsage`
8. 工具和 MCP 必须独立模块化
9. 仪表盘与监控接口必须可直接支撑前端图表
10. 前端必须按页面模块封装 `api/*.ts`

---

如果你要，我下一步可以直接继续补成 **字段级 OpenAPI 风格版**，也就是把这些接口展开成更规范的请求/响应 DTO 清单。
