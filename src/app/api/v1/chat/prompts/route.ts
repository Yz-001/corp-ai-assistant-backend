import { NextRequest } from 'next/server'
import { withErrorHandler, requireAuth, success, db } from '@/lib/api'

// GET /api/v1/chat/prompts - Get prompt tags
export const GET = withErrorHandler(async (req: NextRequest) => {
  const auth = await requireAuth()
  const channel = req.nextUrl.searchParams.get('channel') || 'web'

  const configs = await db.promptConfig.findMany({
    where: {
      tenantId: auth.tenantId,
      type: 'tag',
      enabled: true,
      OR: [{ channel }, { scope: 'global' }],
    },
    orderBy: { sortOrder: 'asc' },
  })

  // Also get global (no tenant) tags
  const globalConfigs = await db.promptConfig.findMany({
    where: {
      type: 'tag',
      enabled: true,
      scope: 'global',
      tenantId: 'global',
    },
    orderBy: { sortOrder: 'asc' },
  })

  const tags = [...new Set([...globalConfigs, ...configs].map(c => c.title))]

  return success({ tags })
})
