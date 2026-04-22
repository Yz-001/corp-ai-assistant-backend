import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// GET /api/v1/admin/mcp/servers - List MCP servers
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const servers = await db.mcpServer.findMany({ orderBy: { createdAt: 'desc' } })

  const enriched = await Promise.all(servers.map(async s => {
    const toolCount = await db.mcpTool.count({ where: { serverId: s.id } })
    return {
      serverId: s.id,
      name: s.name,
      baseUrl: s.baseUrl,
      authType: s.authType,
      status: s.status,
      timeoutSeconds: s.timeoutSeconds,
      lastCheckAt: s.lastCheckAt,
      lastCheckStatus: s.lastCheckStatus,
      description: s.description,
      toolCount,
    }
  }))

  return success({ list: enriched, total: enriched.length, pageNum: 1, pageSize: 100 })
})

// POST /api/v1/admin/mcp/servers - Create MCP server
export const POST = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const { name, baseUrl, authType, authConfig, timeoutSeconds, description } = await req.json()
  if (!name || !baseUrl) return ERR.BAD_REQUEST('name/baseUrl 必填')

  const server = await db.mcpServer.create({
    data: {
      name, baseUrl,
      authType: authType || 'none',
      authConfigJson: JSON.stringify(authConfig || {}),
      timeoutSeconds: timeoutSeconds || 20,
      description: description || '',
    },
  })
  return success(server)
})
