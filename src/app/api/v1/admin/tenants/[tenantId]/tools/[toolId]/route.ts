import { NextRequest } from 'next/server'
import { success, fail, ERR, requireSuperAdmin, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const PUT = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ tenantId: string; toolId: string }> }) => {
  await requireSuperAdmin()
  const { tenantId, toolId } = await params

  // Verify tenant and tool exist
  const tenant = await db.tenant.findUnique({ where: { id: tenantId } })
  if (!tenant) return ERR.NOT_FOUND('租户不存在')

  const tool = await db.toolDefinition.findUnique({ where: { id: toolId } })
  if (!tool) return ERR.NOT_FOUND('工具不存在')

  const body = await req.json()
  const { enabled, config } = body

  if (enabled === undefined) return fail(4001, 'enabled 必填', 400)

  // Upsert tenant tool permission
  const existing = await db.tenantToolPermission.findUnique({
    where: { tenantId_toolId: { tenantId, toolId } },
  })

  let perm
  if (existing) {
    perm = await db.tenantToolPermission.update({
      where: { id: existing.id },
      data: {
        enabled,
        ...(config !== undefined ? { configJson: typeof config === 'string' ? config : JSON.stringify(config) } : {}),
      },
    })
  } else {
    perm = await db.tenantToolPermission.create({
      data: {
        tenantId,
        toolId,
        enabled,
        configJson: config ? (typeof config === 'string' ? config : JSON.stringify(config)) : '{}',
      },
    })
  }

  return success(perm, '更新成功')
})
