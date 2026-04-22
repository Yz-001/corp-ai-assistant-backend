import { NextRequest } from 'next/server'
import { success, requireAuth, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const GET = withErrorHandler(async (req: NextRequest) => {
  const authUser = await requireAuth()

  // 查询完整用户信息及租户
  const user = await db.user.findUnique({
    where: { id: authUser.userId },
    include: { tenant: true },
  })

  if (!user) {
    throw new Error('UNAUTHORIZED')
  }

  // 根据角色生成权限列表
  const permissions = getRolePermissions(user.role)

  return success({
    userId: user.id,
    username: user.username,
    email: user.email,
    role: user.role,
    tenantId: user.tenantId,
    tenantName: user.tenant?.name ?? '',
    permissions,
  })
})

function getRolePermissions(role: string): string[] {
  switch (role) {
    case 'super_admin':
      return ['*']
    case 'tenant_admin':
      return [
        'chat:access',
        'document:read',
        'document:write',
        'document:delete',
        'tool:read',
        'tool:use',
        'user:read',
        'user:write',
        'tenant:config',
        'analytics:read',
      ]
    case 'tenant_user':
      return [
        'chat:access',
        'document:read',
        'document:write',
        'tool:read',
        'tool:use',
      ]
    case 'public_user':
      return ['chat:access']
    default:
      return []
  }
}
