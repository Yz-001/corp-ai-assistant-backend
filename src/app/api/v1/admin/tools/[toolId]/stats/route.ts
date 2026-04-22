import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// GET /api/v1/admin/tools/[toolId]/stats
export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ toolId: string }> }) => {
  await requireAdmin()
  const { toolId } = await params
  const dateType = req.nextUrl.searchParams.get('dateType') || '7d'

  const tool = await db.toolDefinition.findUnique({ where: { id: toolId } })
  if (!tool) return ERR.NOT_FOUND('工具不存在')

  const days = dateType === '30d' ? 30 : 7
  const since = new Date(Date.now() - days * 86400000)

  const [callCount, failCount, avgLatency] = await Promise.all([
    db.toolCallLog.count({ where: { toolId, createdAt: { gte: since } } }),
    db.toolCallLog.count({ where: { toolId, status: 'failed', createdAt: { gte: since } } }),
    db.toolCallLog.aggregate({ _avg: { latencyMs: true }, where: { toolId, createdAt: { gte: since } } }),
  ])

  // Daily trend
  const logs = await db.toolCallLog.findMany({
    where: { toolId, createdAt: { gte: since } },
    select: { createdAt: true, latencyMs: true, status: true },
    orderBy: { createdAt: 'asc' },
  })

  const trendByDate: Record<string, { count: number; failCount: number; totalLatency: number }> = {}
  for (const log of logs) {
    const date = log.createdAt.toISOString().slice(0, 10)
    if (!trendByDate[date]) trendByDate[date] = { count: 0, failCount: 0, totalLatency: 0 }
    trendByDate[date].count++
    if (log.status === 'failed') trendByDate[date].failCount++
    trendByDate[date].totalLatency += log.latencyMs
  }

  const trend = Object.entries(trendByDate).map(([date, v]) => ({
    date,
    callCount: v.count,
    errorRate: v.count > 0 ? Number((v.failCount / v.count * 100).toFixed(2)) : 0,
    avgLatencyMs: v.count > 0 ? Math.round(v.totalLatency / v.count) : 0,
  }))

  return success({
    callCount,
    errorRate: callCount > 0 ? Number((failCount / callCount * 100).toFixed(2)) : 0,
    avgLatencyMs: Math.round(avgLatency._avg.latencyMs || 0),
    trend,
  })
})
