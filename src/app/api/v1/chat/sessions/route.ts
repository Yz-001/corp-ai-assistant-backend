import { NextRequest } from 'next/server'
import { withErrorHandler, requireAuth, success, ERR, paginateQuery, parsePage, db } from '@/lib/api'

// POST /api/v1/chat/sessions - Create session
export const POST = withErrorHandler(async (req: NextRequest) => {
  const auth = await requireAuth()
  const body = await req.json()
  const { title, channel } = body

  const session = await db.chatSession.create({
    data: {
      tenantId: auth.tenantId,
      userId: auth.userId,
      title: title || '新会话',
      channel: channel || 'web',
      status: 'active',
    },
  })

  return success(session)
})

// GET /api/v1/chat/sessions - List sessions
export const GET = withErrorHandler(async (req: NextRequest) => {
  const auth = await requireAuth()
  const { pageNum, pageSize } = parsePage(req.nextUrl.searchParams)
  const keyword = req.nextUrl.searchParams.get('keyword') || ''

  const where: any = {
    tenantId: auth.tenantId,
    userId: auth.userId,
    status: { not: 'deleted' },
  }
  if (keyword) {
    where.title = { contains: keyword }
  }

  const result = await paginateQuery('ChatSession', where, pageNum, pageSize, { lastMessageAt: 'desc' })

  return success(result)
})
