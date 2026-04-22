import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/monitor/tokens
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const dateType = req.nextUrl.searchParams.get('dateType') || '24h'

  const minutesAgo = dateType === '7d' ? 7 * 24 * 60 : 24 * 60
  const since = new Date(Date.now() - minutesAgo * 60 * 1000)

  const qaLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: since } },
    select: { totalTokens: true, createdAt: true },
    orderBy: { createdAt: 'asc' },
  })

  const totalTokens = qaLogs.reduce((sum, l) => sum + l.totalTokens, 0)
  const tokensPerMinute = minutesAgo > 0 ? Number((totalTokens / minutesAgo).toFixed(2)) : 0

  // Trend by hour
  const trendMap: Record<string, number> = {}
  for (const log of qaLogs) {
    const hour = log.createdAt.toISOString().slice(0, 13) + ':00'
    trendMap[hour] = (trendMap[hour] || 0) + log.totalTokens
  }
  const trendList = Object.entries(trendMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([time, value]) => ({ time, value }))

  return success({ totalTokens, tokensPerMinute, trendList })
})
