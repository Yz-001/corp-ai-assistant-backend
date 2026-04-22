import { NextRequest } from 'next/server'
import { success, ERR, requireAdmin, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ logId: string }> }) => {
  const user = await requireAdmin()
  const { logId } = await params

  const log = await db.toolCallLog.findUnique({ where: { id: logId } })
  if (!log) return ERR.NOT_FOUND('日志不存在')

  // Access check
  if (user.role !== 'super_admin' && log.tenantId !== user.tenantId) {
    return ERR.FORBIDDEN()
  }

  return success(log)
})
