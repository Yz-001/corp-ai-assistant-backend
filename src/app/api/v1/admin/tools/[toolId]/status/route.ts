import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// PATCH /api/v1/admin/tools/[toolId]/status
export const PATCH = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ toolId: string }> }) => {
  await requireAdmin()
  const { toolId } = await params
  const { status } = await req.json()
  if (!['enabled', 'disabled'].includes(status)) return ERR.BAD_REQUEST('status 无效')

  const tool = await db.toolDefinition.findUnique({ where: { id: toolId } })
  if (!tool) return ERR.NOT_FOUND('工具不存在')

  await db.toolDefinition.update({ where: { id: toolId }, data: { status } })
  return success(null, '状态更新成功')
})
