import { NextRequest } from 'next/server'
import { requireAuth, ERR, db } from '@/lib/api'

// POST /api/v1/chat/messages/stream - SSE streaming
export async function POST(req: NextRequest) {
  try {
    const auth = await requireAuth()
    const { sessionId, query, channel } = await req.json()
    if (!sessionId || !query) return ERR.BAD_REQUEST('sessionId 和 query 必填')

    const session = await db.chatSession.findFirst({
      where: { id: sessionId, tenantId: auth.tenantId, userId: auth.userId, status: 'active' },
    })
    if (!session) return ERR.NOT_FOUND('会话不存在')

    // Create user message
    await db.chatMessage.create({
      data: { tenantId: auth.tenantId, sessionId, role: 'user', content: query, status: 'done' },
    })

    const placeholderAnswer = `您好！关于"${query.slice(0, 30)}"，这是一个流式模拟回复。实际回答将由 AI 模型生成。`
    const tokenUsage = { promptTokens: 100, completionTokens: 50, totalTokens: 150 }

    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      async start(controller) {
        const send = (event: string, data: any) => {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`))
        }

        // message_start
        const assistantMsg = await db.chatMessage.create({
          data: {
            tenantId: auth.tenantId, sessionId, role: 'assistant',
            content: '', status: 'generating',
          },
        })
        send('message_start', { messageId: assistantMsg.id })

        // Simulate streaming - send answer in chunks
        const chunks = placeholderAnswer.match(/.{1,5}/g) || [placeholderAnswer]
        let fullContent = ''
        for (const chunk of chunks) {
          fullContent += chunk
          send('delta', { content: chunk })
          await new Promise(r => setTimeout(r, 50))
        }

        // sources
        send('sources', { sources: [] })

        // message_end
        await db.chatMessage.update({
          where: { id: assistantMsg.id },
          data: {
            content: fullContent, status: 'done',
            sourcesJson: '[]', toolCallsJson: '[]',
            tokenUsageJson: JSON.stringify(tokenUsage),
          },
        })
        await db.chatSession.update({ where: { id: sessionId }, data: { lastMessageAt: new Date() } })

        // Log QA
        await db.qaLog.create({
          data: {
            tenantId: auth.tenantId, userId: auth.userId, sessionId,
            query, answer: fullContent, modelName: 'placeholder',
            latencyMs: 200, promptTokens: tokenUsage.promptTokens,
            completionTokens: tokenUsage.completionTokens,
            totalTokens: tokenUsage.totalTokens, sourceCount: 0, status: 'success',
          },
        })

        send('message_end', { tokenUsage })
        controller.close()
      },
    })

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    })
  } catch (e: any) {
    const authErr = (() => {
      if (e.message === 'UNAUTHORIZED') return ERR.UNAUTHORIZED()
      if (e.message === 'FORBIDDEN') return ERR.FORBIDDEN()
      return null
    })()
    if (authErr) return authErr
    return ERR.SERVER_ERROR(e.message)
  }
}
