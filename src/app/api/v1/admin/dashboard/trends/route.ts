import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/dashboard/trends
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const dateType = req.nextUrl.searchParams.get('dateType') || '7d'
  const days = dateType === '30d' ? 30 : 7
  const since = new Date(Date.now() - days * 86400000)

  // Get QA logs for trend
  const qaLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: since } },
    select: { createdAt: true, totalTokens: true, status: true, latencyMs: true },
    orderBy: { createdAt: 'asc' },
  })

  // Get usage records for request trend
  const usageRecords = await db.usageRecord.findMany({
    where: { statDate: { gte: since.toISOString().slice(0, 10) } },
  })

  // Aggregate by date
  const dateMap: Record<string, { qa: number; tokens: number; requests: number; errors: number }> = {}
  for (let i = 0; i < days; i++) {
    const d = new Date(Date.now() - (days - 1 - i) * 86400000).toISOString().slice(0, 10)
    dateMap[d] = { qa: 0, tokens: 0, requests: 0, errors: 0 }
  }

  for (const log of qaLogs) {
    const d = log.createdAt.toISOString().slice(0, 10)
    if (dateMap[d]) {
      dateMap[d].qa++
      dateMap[d].tokens += log.totalTokens
      dateMap[d].requests++
      if (log.status === 'failed') dateMap[d].errors++
    }
  }

  for (const rec of usageRecords) {
    if (dateMap[rec.statDate]) {
      dateMap[rec.statDate].requests += rec.requestCount
    }
  }

  const qaTrend = Object.entries(dateMap).map(([date, v]) => ({ date, value: v.qa }))
  const tokenTrend = Object.entries(dateMap).map(([date, v]) => ({ date, value: v.tokens }))
  const requestTrend = Object.entries(dateMap).map(([date, v]) => ({ date, value: v.requests }))
  const errorTrend = Object.entries(dateMap).map(([date, v]) => ({ date, value: v.errors }))

  return success({ qaTrend, tokenTrend, requestTrend, errorTrend })
})
