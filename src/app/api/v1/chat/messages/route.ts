import { NextRequest } from 'next/server'
import { withErrorHandler, requireAuth, success, ERR, db } from '@/lib/api'

// POST /api/v1/chat/messages - Send message (non-streaming)
export const POST = withErrorHandler(async (req: NextRequest) => {
  const auth = await requireAuth()
  const { sessionId, query, channel } = await req.json()
  if (!sessionId || !query) return ERR.BAD_REQUEST('sessionId 和 query 必填')

  // Verify session
  const session = await db.chatSession.findFirst({
    where: { id: sessionId, tenantId: auth.tenantId, userId: auth.userId, status: 'active' },
  })
  if (!session) return ERR.NOT_FOUND('会话不存在')

  // Create user message
  await db.chatMessage.create({
    data: { tenantId: auth.tenantId, sessionId, role: 'user', content: query, status: 'done' },
  })

  // TODO: Real RAG/LLM call - using placeholder for now
  const startTime = Date.now()
  const placeholderAnswer = `您好！关于"${query.slice(0, 30)}"，这是一个模拟回复。实际回答将由 AI 模型生成。`
  const latencyMs = Date.now() - startTime

  const tokenUsage = { promptTokens: 100, completionTokens: 50, totalTokens: 150 }
  const sources: any[] = []

  // Create assistant message
  const assistantMsg = await db.chatMessage.create({
    data: {
      tenantId: auth.tenantId,
      sessionId,
      role: 'assistant',
      content: placeholderAnswer,
      status: 'done',
      sourcesJson: JSON.stringify(sources),
      toolCallsJson: '[]',
      tokenUsageJson: JSON.stringify(tokenUsage),
    },
  })

  // Update session lastMessageAt
  await db.chatSession.update({ where: { id: sessionId }, data: { lastMessageAt: new Date() } })

  // Log QA
  await db.qaLog.create({
    data: {
      tenantId: auth.tenantId,
      userId: auth.userId,
      sessionId,
      query,
      answer: placeholderAnswer,
      modelName: 'placeholder',
      latencyMs,
      promptTokens: tokenUsage.promptTokens,
      completionTokens: tokenUsage.completionTokens,
      totalTokens: tokenUsage.totalTokens,
      sourceCount: sources.length,
      status: 'success',
    },
  })

  return success({
    messageId: assistantMsg.id,
    answer: placeholderAnswer,
    sources,
    toolCalls: [],
    tokenUsage,
    latencyMs,
  })
})
