import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// PATCH /api/v1/admin/mcp/servers/[serverId]/status
export const PATCH = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ serverId: string }> }) => {
  await requireAdmin()
  const { serverId } = await params
  const { status } = await req.json()
  if (!['enabled', 'disabled'].includes(status)) return ERR.BAD_REQUEST('status 无效')

  const server = await db.mcpServer.findUnique({ where: { id: serverId } })
  if (!server) return ERR.NOT_FOUND('MCP服务不存在')

  await db.mcpServer.update({ where: { id: serverId }, data: { status } })
  return success(null, '状态更新成功')
})
