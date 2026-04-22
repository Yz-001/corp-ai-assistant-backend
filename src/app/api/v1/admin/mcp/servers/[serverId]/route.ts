import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// GET /api/v1/admin/mcp/servers/[serverId]
export const GET = withErrorHandler(async (_req: NextRequest, { params }: { params: Promise<{ serverId: string }> }) => {
  await requireAdmin()
  const { serverId } = await params

  const server = await db.mcpServer.findUnique({
    where: { id: serverId },
    include: { mcpTools: true },
  })
  if (!server) return ERR.NOT_FOUND('MCP服务不存在')

  return success({
    serverId: server.id,
    name: server.name,
    baseUrl: server.baseUrl,
    authType: server.authType,
    authConfig: JSON.parse(server.authConfigJson || '{}'),
    status: server.status,
    timeoutSeconds: server.timeoutSeconds,
    description: server.description,
    lastCheckAt: server.lastCheckAt,
    lastCheckStatus: server.lastCheckStatus,
    tools: server.mcpTools.map(t => ({
      id: t.id,
      toolCode: t.toolCode,
      toolName: t.toolName,
      description: t.description,
      status: t.status,
    })),
  })
})

// PUT /api/v1/admin/mcp/servers/[serverId]
export const PUT = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ serverId: string }> }) => {
  await requireAdmin()
  const { serverId } = await params
  const { name, baseUrl, authType, authConfig, timeoutSeconds, description } = await req.json()

  const server = await db.mcpServer.findUnique({ where: { id: serverId } })
  if (!server) return ERR.NOT_FOUND('MCP服务不存在')

  const updated = await db.mcpServer.update({
    where: { id: serverId },
    data: {
      ...(name !== undefined && { name }),
      ...(baseUrl !== undefined && { baseUrl }),
      ...(authType !== undefined && { authType }),
      ...(authConfig !== undefined && { authConfigJson: JSON.stringify(authConfig) }),
      ...(timeoutSeconds !== undefined && { timeoutSeconds }),
      ...(description !== undefined && { description }),
    },
  })
  return success(updated)
})
