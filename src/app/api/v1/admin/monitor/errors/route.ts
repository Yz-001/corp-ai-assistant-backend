import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/monitor/errors
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const dateType = req.nextUrl.searchParams.get('dateType') || '24h'

  const minutesAgo = dateType === '7d' ? 7 * 24 * 60 : 24 * 60
  const since = new Date(Date.now() - minutesAgo * 60 * 1000)

  const [total, failed] = await Promise.all([
    db.qaLog.count({ where: { createdAt: { gte: since } } }),
    db.qaLog.count({ where: { createdAt: { gte: since }, status: 'failed' } }),
  ])

  const errorRate = total > 0 ? Number((failed / total).toFixed(4)) : 0

  // Trend by hour
  const qaLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: since } },
    select: { status: true, createdAt: true },
    orderBy: { createdAt: 'asc' },
  })

  const trendMap: Record<string, { total: number; failed: number }> = {}
  for (const log of qaLogs) {
    const hour = log.createdAt.toISOString().slice(0, 13) + ':00'
    if (!trendMap[hour]) trendMap[hour] = { total: 0, failed: 0 }
    trendMap[hour].total++
    if (log.status === 'failed') trendMap[hour].failed++
  }

  const errorTrend = Object.entries(trendMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([time, v]) => ({ time, errorRate: v.total > 0 ? Number((v.failed / v.total).toFixed(4)) : 0, errorCount: v.failed }))

  return success({ errorRate, errorTrend })
})
