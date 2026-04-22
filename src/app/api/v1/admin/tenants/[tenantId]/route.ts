import { NextRequest } from 'next/server'
import { success, fail, ERR, requireSuperAdmin, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ tenantId: string }> }) => {
  await requireSuperAdmin()
  const { tenantId } = await params

  const tenant = await db.tenant.findUnique({ where: { id: tenantId } })
  if (!tenant) return ERR.NOT_FOUND('租户不存在')

  // Attach counts
  const [userCount, documentCount, requestResult, tokenResult] = await Promise.all([
    db.user.count({ where: { tenantId } }),
    db.document.count({ where: { tenantId } }),
    db.usageRecord.aggregate({ where: { tenantId }, _sum: { requestCount: true } }),
    db.usageRecord.aggregate({ where: { tenantId }, _sum: { tokenCount: true } }),
  ])

  return success({
    ...tenant,
    userCount,
    documentCount,
    requestCount: requestResult._sum.requestCount || 0,
    tokenCount: tokenResult._sum.tokenCount || 0,
  })
})

export const PUT = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ tenantId: string }> }) => {
  await requireSuperAdmin()
  const { tenantId } = await params

  const tenant = await db.tenant.findUnique({ where: { id: tenantId } })
  if (!tenant) return ERR.NOT_FOUND('租户不存在')

  const body = await req.json()
  const { name, type, planType, quotaConfig, configJson } = body

  const data: any = {}
  if (name !== undefined) data.name = name
  if (type !== undefined) data.type = type
  if (planType !== undefined) data.planType = planType
  if (quotaConfig !== undefined) data.quotaJson = typeof quotaConfig === 'string' ? quotaConfig : JSON.stringify(quotaConfig)
  if (configJson !== undefined) data.configJson = typeof configJson === 'string' ? configJson : JSON.stringify(configJson)

  const updated = await db.tenant.update({ where: { id: tenantId }, data })

  return success(updated, '更新成功')
})
