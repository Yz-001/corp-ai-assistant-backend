import { NextRequest } from 'next/server'
import { withErrorHandler, requireAuth, success, db } from '@/lib/api'

// GET /api/v1/chat/suggestions - Get suggested questions
export const GET = withErrorHandler(async (req: NextRequest) => {
  const auth = await requireAuth()
  const channel = req.nextUrl.searchParams.get('channel') || 'web'

  const [tenantConfigs, globalConfigs] = await Promise.all([
    db.promptConfig.findMany({
      where: { tenantId: auth.tenantId, type: 'suggested_question', enabled: true, OR: [{ channel }, { scope: 'global' }] },
      orderBy: { sortOrder: 'asc' },
    }),
    db.promptConfig.findMany({
      where: { type: 'suggested_question', enabled: true, scope: 'global', tenantId: 'global' },
      orderBy: { sortOrder: 'asc' },
    }),
  ])

  const suggestions = [...globalConfigs, ...tenantConfigs].map(c => c.content)

  return success({ suggestions })
})
