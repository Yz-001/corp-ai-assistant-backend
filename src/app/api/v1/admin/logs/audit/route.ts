import { NextRequest } from 'next/server'
import { success, ERR, requireAdmin, withErrorHandler, paginateQuery, parsePage } from '@/lib/api'
import { db } from '@/lib/db'
import { Prisma } from '@prisma/client'

export const GET = withErrorHandler(async (req: NextRequest) => {
  const user = await requireAdmin()

  const sp = req.nextUrl.searchParams
  const { pageNum, pageSize } = parsePage(sp)
  const moduleFilter = sp.get('module') || undefined
  const actionFilter = sp.get('action') || undefined
  const startTime = sp.get('startTime') || undefined
  const endTime = sp.get('endTime') || undefined
  const tenantIdParam = sp.get('tenantId') || undefined

  const where: Prisma.AuditLogWhereInput = {}

  if (user.role === 'super_admin') {
    if (tenantIdParam) where.tenantId = tenantIdParam
  } else {
    where.tenantId = user.tenantId
  }

  if (moduleFilter) where.module = moduleFilter
  if (actionFilter) where.action = actionFilter
  if (startTime || endTime) {
    where.createdAt = {}
    if (startTime) (where.createdAt as any).gte = new Date(startTime)
    if (endTime) (where.createdAt as any).lte = new Date(endTime)
  }

  const result = await paginateQuery('AuditLog', where, pageNum, pageSize)

  return success(result)
})
