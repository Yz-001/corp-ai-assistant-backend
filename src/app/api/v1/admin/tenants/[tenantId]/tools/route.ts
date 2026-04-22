import { NextRequest } from 'next/server'
import { success, ERR, requireSuperAdmin, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ tenantId: string }> }) => {
  await requireSuperAdmin()
  const { tenantId } = await params

  const tenant = await db.tenant.findUnique({ where: { id: tenantId } })
  if (!tenant) return ERR.NOT_FOUND('租户不存在')

  // Get all tool definitions with this tenant's permissions
  const tools = await db.toolDefinition.findMany({
    where: { status: 'enabled' },
    include: {
      tenantToolPerms: {
        where: { tenantId },
      },
    },
    orderBy: { name: 'asc' },
  })

  const result = tools.map((tool) => {
    const perm = tool.tenantToolPerms[0]
    return {
      toolId: tool.id,
      code: tool.code,
      name: tool.name,
      type: tool.type,
      description: tool.description,
      enabled: perm?.enabled ?? false,
      configJson: perm?.configJson ?? '{}',
      permissionId: perm?.id ?? null,
    }
  })

  return success(result)
})
