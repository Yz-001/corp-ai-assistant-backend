import { NextRequest } from 'next/server'
import { success, fail, ERR, requireSuperAdmin, withErrorHandler, paginateQuery, parsePage } from '@/lib/api'
import { db } from '@/lib/db'
import { Prisma } from '@prisma/client'

export const GET = withErrorHandler(async (req: NextRequest) => {
  await requireSuperAdmin()

  const sp = req.nextUrl.searchParams
  const { pageNum, pageSize } = parsePage(sp)
  const keyword = sp.get('keyword') || undefined
  const status = sp.get('status') || undefined
  const type = sp.get('type') || undefined

  const where: Prisma.TenantWhereInput = {}
  if (keyword) {
    where.OR = [
      { name: { contains: keyword } },
      { code: { contains: keyword } },
    ]
  }
  if (status) where.status = status
  if (type) where.type = type

  const result = await paginateQuery('Tenant', where, pageNum, pageSize)

  // Attach aggregated counts for each tenant
  const tenantsWithCounts = await Promise.all(
    result.list.map(async (t: any) => {
      const [userCount, documentCount, requestCount, tokenCount] = await Promise.all([
        db.user.count({ where: { tenantId: t.id } }),
        db.document.count({ where: { tenantId: t.id } }),
        db.usageRecord.aggregate({ where: { tenantId: t.id }, _sum: { requestCount: true } }),
        db.usageRecord.aggregate({ where: { tenantId: t.id }, _sum: { tokenCount: true } }),
      ])
      return {
        ...t,
        userCount,
        documentCount,
        requestCount: requestCount._sum.requestCount || 0,
        tokenCount: tokenCount._sum.tokenCount || 0,
      }
    })
  )

  return success({ ...result, list: tenantsWithCounts })
})

export const POST = withErrorHandler(async (req: NextRequest) => {
  await requireSuperAdmin()

  const body = await req.json()
  const { name, code, type, planType, status, quotaConfig } = body

  if (!name || !code) return fail(4001, 'name 和 code 必填', 400)

  // Check uniqueness
  const existing = await db.tenant.findUnique({ where: { code } })
  if (existing) return ERR.DUPLICATE('租户编码已存在')

  const tenant = await db.tenant.create({
    data: {
      name,
      code,
      type: type || 'enterprise',
      planType: planType || 'basic',
      status: status || 'enabled',
      quotaJson: quotaConfig ? JSON.stringify(quotaConfig) : '{}',
    },
  })

  return success(tenant, '创建成功')
})
