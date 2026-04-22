import { NextRequest } from 'next/server'
import { success, ERR, requireSuperAdmin, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ tenantId: string }> }) => {
  await requireSuperAdmin()
  const { tenantId } = await params

  const tenant = await db.tenant.findUnique({ where: { id: tenantId } })
  if (!tenant) return ERR.NOT_FOUND('租户不存在')

  const sp = req.nextUrl.searchParams
  const dateType = sp.get('dateType') || '7d'
  const days = dateType === '30d' ? 30 : 7

  // Calculate date range
  const now = new Date()
  const startDate = new Date(now.getTime() - days * 24 * 3600 * 1000)
  const startDateStr = startDate.toISOString().slice(0, 10)

  // Aggregate usage records by date
  const records = await db.usageRecord.findMany({
    where: {
      tenantId,
      statDate: { gte: startDateStr },
    },
    orderBy: { statDate: 'asc' },
  })

  // Aggregate totals
  const totals = records.reduce(
    (acc, r) => ({
      requestCount: acc.requestCount + r.requestCount,
      tokenCount: acc.tokenCount + r.tokenCount,
      cost: acc.cost + r.cost,
    }),
    { requestCount: 0, tokenCount: 0, cost: 0 }
  )

  // Group by serviceType
  const byService = records.reduce((acc: any, r) => {
    if (!acc[r.serviceType]) acc[r.serviceType] = { requestCount: 0, tokenCount: 0, cost: 0 }
    acc[r.serviceType].requestCount += r.requestCount
    acc[r.serviceType].tokenCount += r.tokenCount
    acc[r.serviceType].cost += r.cost
    return acc
  }, {})

  // Group by date
  const byDate = records.reduce((acc: any, r) => {
    if (!acc[r.statDate]) acc[r.statDate] = { requestCount: 0, tokenCount: 0, cost: 0 }
    acc[r.statDate].requestCount += r.requestCount
    acc[r.statDate].tokenCount += r.tokenCount
    acc[r.statDate].cost += r.cost
    return acc
  }, {})

  return success({ totals, byService, byDate, days })
})
