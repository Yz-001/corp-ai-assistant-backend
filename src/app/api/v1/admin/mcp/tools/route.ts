import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, parsePage, db } from '@/lib/api'

// GET /api/v1/admin/mcp/tools - List MCP tools
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const { pageNum, pageSize } = parsePage(req.nextUrl.searchParams)

  const where: any = {}
  const result = await db.mcpTool.findMany({
    where,
    include: { server: { select: { id: true, name: true, baseUrl: true } } },
    orderBy: { createdAt: 'desc' },
  })

  const total = result.length
  const start = (pageNum - 1) * pageSize
  const list = result.slice(start, start + pageSize).map(t => ({
    id: t.id,
    serverId: t.serverId,
    serverName: t.server.name,
    toolCode: t.toolCode,
    toolName: t.toolName,
    description: t.description,
    schema: JSON.parse(t.schemaJson || '{}'),
    status: t.status,
    createdAt: t.createdAt,
  }))

  return success({ list, total, pageNum, pageSize })
})
