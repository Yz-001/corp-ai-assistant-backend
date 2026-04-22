import { NextRequest } from 'next/server'
import { success, ERR, requireAuth, withErrorHandler, paginateQuery, parsePage } from '@/lib/api'
import { db } from '@/lib/db'
import { Prisma } from '@prisma/client'

export const GET = withErrorHandler(async (req: NextRequest) => {
  const user = await requireAuth()

  const sp = req.nextUrl.searchParams
  const { pageNum, pageSize } = parsePage(sp)
  const keyword = sp.get('keyword') || undefined
  const status = sp.get('status') || undefined
  const visibility = sp.get('visibility') || undefined
  const fileType = sp.get('fileType') || undefined
  const tenantIdParam = sp.get('tenantId') || undefined

  // Build where clause
  const where: Prisma.DocumentWhereInput = {}

  // tenant_admin sees own tenant; super_admin sees all (or filtered)
  if (user.role === 'super_admin') {
    if (tenantIdParam) where.tenantId = tenantIdParam
  } else if (user.role === 'tenant_admin') {
    where.tenantId = user.tenantId
  } else {
    where.tenantId = user.tenantId
    where.visibility = 'public'
  }

  if (status) where.status = status
  if (visibility) where.visibility = visibility
  if (fileType) where.fileType = fileType
  if (keyword) {
    where.name = { contains: keyword }
  }

  const result = await paginateQuery('Document', where, pageNum, pageSize)

  return success(result)
})
