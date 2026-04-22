import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/monitor/traffic
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const dateType = req.nextUrl.searchParams.get('dateType') || '24h'

  const minutesAgo = dateType === '7d' ? 7 * 24 * 60 : 24 * 60
  const since = new Date(Date.now() - minutesAgo * 60 * 1000)

  const qaLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: since } },
    select: { createdAt: true },
    orderBy: { createdAt: 'asc' },
  })

  const totalMinutes = minutesAgo
  const requestPerMinute = totalMinutes > 0 ? Number((qaLogs.length / totalMinutes).toFixed(2)) : 0

  // Build trend by hour
  const trendMap: Record<string, number> = {}
  for (const log of qaLogs) {
    const hour = log.createdAt.toISOString().slice(0, 13) + ':00'
    trendMap[hour] = (trendMap[hour] || 0) + 1
  }
  const requestTrend = Object.entries(trendMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([time, count]) => ({ time, count }))

  return success({ requestPerMinute, requestTrend })
})
