import { NextRequest } from 'next/server'
import { success, ERR, requireAdmin, withErrorHandler, paginateQuery, parsePage } from '@/lib/api'
import { db } from '@/lib/db'
import { Prisma } from '@prisma/client'

export const GET = withErrorHandler(async (req: NextRequest) => {
  const user = await requireAdmin()

  const sp = req.nextUrl.searchParams
  const { pageNum, pageSize } = parsePage(sp)
  const keyword = sp.get('keyword') || undefined
  const status = sp.get('status') || undefined
  const userId = sp.get('userId') || undefined
  const startTime = sp.get('startTime') || undefined
  const endTime = sp.get('endTime') || undefined
  const tenantIdParam = sp.get('tenantId') || undefined

  const where: Prisma.QaLogWhereInput = {}

  // tenant_admin sees own tenant; super_admin sees all or filtered
  if (user.role === 'super_admin') {
    if (tenantIdParam) where.tenantId = tenantIdParam
  } else {
    where.tenantId = user.tenantId
  }

  if (userId) where.userId = userId
  if (status) where.status = status
  if (keyword) {
    where.OR = [
      { query: { contains: keyword } },
      { answer: { contains: keyword } },
    ]
  }
  if (startTime || endTime) {
    where.createdAt = {}
    if (startTime) (where.createdAt as any).gte = new Date(startTime)
    if (endTime) (where.createdAt as any).lte = new Date(endTime)
  }

  const result = await paginateQuery('QaLog', where, pageNum, pageSize, undefined, undefined)

  // Enrich with user and tenant info
  const enrichedList = await Promise.all(
    result.list.map(async (log: any) => {
      const [u, t] = await Promise.all([
        log.userId ? db.user.findUnique({ where: { id: log.userId }, select: { id: true, username: true, role: true } }) : null,
        db.tenant.findUnique({ where: { id: log.tenantId }, select: { id: true, name: true, code: true } }),
      ])
      return { ...log, user: u, tenant: t }
    })
  )

  return success({ ...result, list: enrichedList })
})
