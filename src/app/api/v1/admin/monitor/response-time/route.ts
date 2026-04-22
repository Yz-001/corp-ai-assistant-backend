import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/monitor/response-time
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const dateType = req.nextUrl.searchParams.get('dateType') || '24h'

  const minutesAgo = dateType === '7d' ? 7 * 24 * 60 : 24 * 60
  const since = new Date(Date.now() - minutesAgo * 60 * 1000)

  const result = await db.qaLog.aggregate({
    _avg: { latencyMs: true },
    where: { createdAt: { gte: since } },
  })
  const avgLatencyMs = Math.round(result._avg.latencyMs || 0)

  // Trend by hour
  const qaLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: since } },
    select: { latencyMs: true, createdAt: true },
    orderBy: { createdAt: 'asc' },
  })

  const trendMap: Record<string, { total: number; count: number }> = {}
  for (const log of qaLogs) {
    const hour = log.createdAt.toISOString().slice(0, 13) + ':00'
    if (!trendMap[hour]) trendMap[hour] = { total: 0, count: 0 }
    trendMap[hour].total += log.latencyMs
    trendMap[hour].count++
  }

  const latencyTrend = Object.entries(trendMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([time, v]) => ({ time, avgLatencyMs: v.count > 0 ? Math.round(v.total / v.count) : 0 }))

  return success({ avgLatencyMs, latencyTrend })
})
