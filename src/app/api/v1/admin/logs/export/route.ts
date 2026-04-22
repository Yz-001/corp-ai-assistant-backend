import { NextRequest } from 'next/server'
import { success, fail, requireAdmin, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'
import { Prisma } from '@prisma/client'

export const GET = withErrorHandler(async (req: NextRequest) => {
  const user = await requireAdmin()

  const sp = req.nextUrl.searchParams
  const type = sp.get('type') || 'qa'
  const startTime = sp.get('startTime') || undefined
  const endTime = sp.get('endTime') || undefined

  // Tenant filtering
  const tenantFilter: any = {}
  if (user.role !== 'super_admin') {
    tenantFilter.tenantId = user.tenantId
  } else if (sp.get('tenantId')) {
    tenantFilter.tenantId = sp.get('tenantId')
  }

  const dateFilter: any = {}
  if (startTime || endTime) {
    dateFilter.createdAt = {}
    if (startTime) dateFilter.createdAt.gte = new Date(startTime)
    if (endTime) dateFilter.createdAt.lte = new Date(endTime)
  }

  const where = { ...tenantFilter, ...dateFilter }

  let data: any[]

  switch (type) {
    case 'qa': {
      data = await db.qaLog.findMany({ where, orderBy: { createdAt: 'desc' } })
      break
    }
    case 'tools': {
      data = await db.toolCallLog.findMany({ where, orderBy: { createdAt: 'desc' } })
      break
    }
    case 'audit': {
      data = await db.auditLog.findMany({ where, orderBy: { createdAt: 'desc' } })
      break
    }
    default:
      return fail(4001, 'type 必须为 qa、tools 或 audit', 400)
  }

  return success(data)
})
