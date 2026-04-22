import { NextRequest } from 'next/server'
import { success, fail, ERR, requireSuperAdmin, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const PATCH = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ tenantId: string }> }) => {
  await requireSuperAdmin()
  const { tenantId } = await params

  const body = await req.json()
  const { status } = body

  if (!['enabled', 'disabled'].includes(status)) {
    return fail(4001, 'status 必须为 enabled 或 disabled', 400)
  }

  const tenant = await db.tenant.findUnique({ where: { id: tenantId } })
  if (!tenant) return ERR.NOT_FOUND('租户不存在')

  const updated = await db.tenant.update({
    where: { id: tenantId },
    data: { status },
  })

  return success(updated, `租户已${status === 'enabled' ? '启用' : '禁用'}`)
})
