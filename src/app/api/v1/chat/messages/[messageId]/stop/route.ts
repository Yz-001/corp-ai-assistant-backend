import { NextRequest } from 'next/server'
import { withErrorHandler, requireAuth, success, ERR, db } from '@/lib/api'

// POST /api/v1/chat/messages/[messageId]/stop
export const POST = withErrorHandler(async (_req: NextRequest, { params }: { params: Promise<{ messageId: string }> }) => {
  const auth = await requireAuth()
  const { messageId } = await params

  const msg = await db.chatMessage.findFirst({ where: { id: messageId, tenantId: auth.tenantId } })
  if (!msg) return ERR.NOT_FOUND('消息不存在')

  await db.chatMessage.update({ where: { id: messageId }, data: { status: 'stopped' } })
  return success(null, '已停止生成')
})
