import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, db } from '@/lib/api'

// GET /api/v1/admin/dashboard/rankings
export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const dateType = req.nextUrl.searchParams.get('dateType') || '7d'
  const days = dateType === '30d' ? 30 : 7
  const since = new Date(Date.now() - days * 86400000)

  // Tenant ranking by QA count
  const qaLogs = await db.qaLog.findMany({
    where: { createdAt: { gte: since } },
    select: { tenantId: true, query: true },
  })

  const tenantCount: Record<string, number> = {}
  const queryCount: Record<string, number> = {}
  for (const log of qaLogs) {
    tenantCount[log.tenantId] = (tenantCount[log.tenantId] || 0) + 1
    const q = log.query?.slice(0, 50) || ''
    if (q) queryCount[q] = (queryCount[q] || 0) + 1
  }

  // Enrich tenant ranking with names
  const tenantIds = Object.keys(tenantCount)
  const tenants = await db.tenant.findMany({ where: { id: { in: tenantIds } }, select: { id: true, name: true } })
  const tenantNameMap = Object.fromEntries(tenants.map(t => [t.id, t.name]))

  const tenantRanking = Object.entries(tenantCount)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([id, count]) => ({ tenantId: id, tenantName: tenantNameMap[id] || id, count }))

  const hotQuestionRanking = Object.entries(queryCount)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([query, count]) => ({ query, count }))

  // Tool ranking
  const toolLogs = await db.toolCallLog.findMany({
    where: { createdAt: { gte: since } },
    select: { toolName: true },
  })
  const toolCount: Record<string, number> = {}
  for (const log of toolLogs) {
    toolCount[log.toolName] = (toolCount[log.toolName] || 0) + 1
  }
  const toolRanking = Object.entries(toolCount)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10)
    .map(([name, count]) => ({ toolName: name, count }))

  return success({ tenantRanking, toolRanking, hotQuestionRanking })
})
