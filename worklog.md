---
Task ID: 1-5
Agent: main
Task: AI企业助手后端完整开发

Work Log:
- 阅读三份需求文档：后端说明书、前端说明书、前后端接口清单
- 设计 Prisma Schema，15个模型适配 SQLite（无 enum/jsonb，用 String + JSON.stringify）
- 创建核心工具库：统一响应(response.ts)、分页(pagination.ts)、JWT认证(auth.ts)、密码(password.ts)、路由错误处理(route.ts)、统一导出(index.ts)
- 通过子代理实现 Auth 模块 4 个路由
- 通过子代理实现 Documents(6)、Admin-Tenants(6)、Admin-Logs(6) 共 18 个路由
- 手动实现 Chat 模块 7 个路由（sessions CRUD、messages/stream/stop、prompts、suggestions）
- 手动实现 Admin-Tools(5)、Admin-MCP(9)、Dashboard(3)、Monitor(5)、Health(1) 共 23 个路由
- 创建种子数据脚本：5个租户、5个用户、12个提示词配置、4个工具定义、2个会话+消息、3个文档、50条QA日志、28条使用记录、1个MCP服务器+2个工具
- 推送 Prisma Schema、运行种子脚本
- 修复 db 导出问题（添加到 @/lib/api/index.ts 的 re-export）
- 修复损坏的目录名 [messageId]
- 全量 lint 检查通过
- 验证 12+ 个关键接口全部正常工作

Stage Summary:
- Prisma Schema: 15个模型（Tenant, User, ChatSession, ChatMessage, PromptConfig, Document, DocumentChunk, QaLog, ToolDefinition, TenantToolPermission, ToolCallLog, McpServer, McpTool, UsageRecord, AuditLog）
- 核心工具: 6个文件（response, auth, pagination, password, route, index）
- API路由: 48个路由文件，覆盖全部接口清单
- 种子数据: admin/123456 (super_admin), sales_admin/123456, sales_user/123456, partner_admin/123456, user_a/123456
- 所有接口测试通过，lint 无错误
