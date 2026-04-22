import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/monitor/online-users
export const GET = withErrorHandler(async () => {
  await requireAdmin()

  // Online = distinct users with QA activity in last 5 min
  const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000)
  const recentLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: fiveMinAgo } },
    select: { userId: true, createdAt: true },
  })
  const currentOnlineUsers = new Set(recentLogs.map(l => l.userId).filter(Boolean)).size

  // Trend for last 24 hours (hourly buckets)
  const since = new Date(Date.now() - 24 * 3600000)
  const hourlyLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: since } },
    select: { userId: true, createdAt: true },
  })

  const trendMap: Record<string, Set<string>> = {}
  for (const log of hourlyLogs) {
    const hour = log.createdAt.toISOString().slice(0, 13) + ':00'
    if (!trendMap[hour]) trendMap[hour] = new Set()
    if (log.userId) trendMap[hour].add(log.userId)
  }

  const trendList = Object.entries(trendMap)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([time, users]) => ({ time, count: users.size }))

  return success({ currentOnlineUsers, trendList })
})
