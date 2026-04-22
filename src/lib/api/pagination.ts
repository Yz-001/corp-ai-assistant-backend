import { db } from '@/lib/db'
import { Prisma } from '@prisma/client'

// 统一分页查询
export async function paginateQuery<T extends Prisma.ModelName>(
  model: T,
  where: any,
  pageNum: number = 1,
  pageSize: number = 20,
  orderBy: any = { createdAt: 'desc' },
  include?: any,
) {
  const skip = (pageNum - 1) * pageSize
  const [list, total] = await Promise.all([
    (db as any)[getModelKey(model)].findMany({
      where,
      skip,
      take: pageSize,
      orderBy,
      ...(include ? { include } : {}),
    }),
    (db as any)[getModelKey(model)].count({ where }),
  ])
  return { list, total, pageNum, pageSize }
}

// Prisma model 名 -> db key 映射
function getModelKey(model: Prisma.ModelName): string {
  const map: Record<string, string> = {
    User: 'user',
    Tenant: 'tenant',
    ChatSession: 'chatSession',
    ChatMessage: 'chatMessage',
    PromptConfig: 'promptConfig',
    Document: 'document',
    DocumentChunk: 'documentChunk',
    QaLog: 'qaLog',
    ToolDefinition: 'toolDefinition',
    TenantToolPermission: 'tenantToolPermission',
    ToolCallLog: 'toolCallLog',
    McpServer: 'mcpServer',
    McpTool: 'mcpTool',
    UsageRecord: 'usageRecord',
    AuditLog: 'auditLog',
  }
  return map[model] || model.charAt(0).toLowerCase() + model.slice(1)
}

// 解析分页参数
export function parsePage(searchParams: URLSearchParams) {
  return {
    pageNum: Math.max(1, Number(searchParams.get('pageNum')) || 1),
    pageSize: Math.min(100, Math.max(1, Number(searchParams.get('pageSize')) || 20)),
  }
}
