import { NextRequest } from 'next/server'
import { withErrorHandler, requireAuth, success, ERR, db } from '@/lib/api'

// GET /api/v1/chat/sessions/[sessionId]
export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ sessionId: string }> }) => {
  const auth = await requireAuth()
  const { sessionId } = await params

  const session = await db.chatSession.findFirst({
    where: { id: sessionId, tenantId: auth.tenantId, userId: auth.userId, status: { not: 'deleted' } },
    include: { messages: { orderBy: { createdAt: 'asc' } } },
  })
  if (!session) return ERR.NOT_FOUND('会话不存在')

  const messages = session.messages.map(m => ({
    messageId: m.id,
    role: m.role,
    content: m.content,
    status: m.status,
    sources: JSON.parse(m.sourcesJson || '[]'),
    toolCalls: JSON.parse(m.toolCallsJson || '[]'),
    tokenUsage: JSON.parse(m.tokenUsageJson || '{}'),
    createdAt: m.createdAt,
  }))

  return success({
    sessionId: session.id,
    title: session.title,
    channel: session.channel,
    status: session.status,
    messages,
  })
})

// PATCH /api/v1/chat/sessions/[sessionId] - Rename
export const PATCH = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ sessionId: string }> }) => {
  const auth = await requireAuth()
  const { sessionId } = await params
  const { title } = await req.json()
  if (!title) return ERR.BAD_REQUEST('标题不能为空')

  const session = await db.chatSession.findFirst({ where: { id: sessionId, tenantId: auth.tenantId, userId: auth.userId } })
  if (!session) return ERR.NOT_FOUND('会话不存在')

  const updated = await db.chatSession.update({ where: { id: sessionId }, data: { title } })
  return success(updated)
})

// DELETE /api/v1/chat/sessions/[sessionId]
export const DELETE = withErrorHandler(async (_req: NextRequest, { params }: { params: Promise<{ sessionId: string }> }) => {
  const auth = await requireAuth()
  const { sessionId } = await params

  const session = await db.chatSession.findFirst({ where: { id: sessionId, tenantId: auth.tenantId, userId: auth.userId } })
  if (!session) return ERR.NOT_FOUND('会话不存在')

  await db.chatSession.update({ where: { id: sessionId }, data: { status: 'deleted' } })
  return success(null, '删除成功')
})
