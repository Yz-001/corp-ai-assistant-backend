import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/dashboard/overview
export const GET = withErrorHandler(async () => {
  await requireAdmin()

  const today = new Date().toISOString().slice(0, 10)
  const todayStart = new Date(today)

  const [qaToday, toolCallsToday, docsToday, qaLogs] = await Promise.all([
    db.qaLog.count({ where: { createdAt: { gte: todayStart } } }),
    db.toolCallLog.count({ where: { createdAt: { gte: todayStart } } }),
    db.document.count({ where: { createdAt: { gte: todayStart } } }),
    db.qaLog.findMany({ where: { createdAt: { gte: todayStart } } }),
  ])

  const totalTokens = qaLogs.reduce((sum, l) => sum + l.totalTokens, 0)
  const totalLatency = qaLogs.reduce((sum, l) => sum + l.latencyMs, 0)
  const failCount = qaLogs.filter(l => l.status === 'failed').length

  // Estimate online users (distinct users in last 5 min)
  const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000)
  const recentQa = await db.qaLog.findMany({
    where: { createdAt: { gte: fiveMinAgo } },
    select: { userId: true },
  })
  const onlineUsers = new Set(recentQa.map(q => q.userId).filter(Boolean)).size

  // Active users today
  const activeUsers = new Set(qaLogs.map(q => q.userId).filter(Boolean)).size

  return success({
    onlineUsers,
    todayActiveUsers: activeUsers,
    todayQaCount: qaToday,
    todayRequestCount: qaToday + toolCallsToday,
    todayTokenCount: totalTokens,
    todayUploadCount: docsToday,
    todayToolCalls: toolCallsToday,
    errorRate: qaToday > 0 ? Number((failCount / qaToday).toFixed(4)) : 0,
    avgLatencyMs: qaToday > 0 ? Math.round(totalLatency / qaToday) : 0,
  })
})
