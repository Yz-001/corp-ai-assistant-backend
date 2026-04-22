import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// POST /api/v1/admin/mcp/servers/[serverId]/discover-tools
export const POST = withErrorHandler(async (_req: NextRequest, { params }: { params: Promise<{ serverId: string }> }) => {
  await requireAdmin()
  const { serverId } = await params

  const server = await db.mcpServer.findUnique({ where: { id: serverId } })
  if (!server) return ERR.NOT_FOUND('MCP服务不存在')

  // TODO: Real MCP tool discovery - return empty for now
  await db.mcpServer.update({
    where: { id: serverId },
    data: { lastCheckAt: new Date(), lastCheckStatus: 'success' },
  })

  return success({ toolList: [] })
})
