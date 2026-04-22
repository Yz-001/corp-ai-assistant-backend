import { NextRequest } from 'next/server'
import { db } from '@/lib/db'
import { success, ERR, verifyPassword, generateToken, withErrorHandler } from '@/lib/api'

export const POST = withErrorHandler(async (req: NextRequest) => {
  const body = await req.json()
  const { username, password } = body

  if (!username || !password) {
    return ERR.BAD_REQUEST('用户名和密码不能为空')
  }

  // 查找用户及租户信息
  const user = await db.user.findUnique({
    where: { username },
    include: { tenant: true },
  })

  if (!user) {
    return ERR.UNAUTHORIZED()
  }

  // 检查用户状态
  if (user.status !== 'enabled') {
    return ERR.FORBIDDEN()
  }

  // 检查租户状态
  if (user.tenant?.status !== 'enabled') {
    return ERR.FORBIDDEN()
  }

  // 验证密码
  if (!verifyPassword(password, user.passwordHash)) {
    return ERR.UNAUTHORIZED()
  }

  // 更新最后登录时间
  await db.user.update({
    where: { id: user.id },
    data: { lastLoginAt: new Date() },
  })

  // 生成 token
  const accessToken = generateToken(user)
  const expiresIn = 7 * 24 * 3600 // 7天，单位秒

  return success({
    accessToken,
    refreshToken: accessToken, // 简易方案：refreshToken 与 accessToken 相同
    expiresIn,
    userInfo: {
      userId: user.id,
      username: user.username,
      role: user.role,
      tenantId: user.tenantId,
      tenantName: user.tenant?.name ?? '',
    },
  })
})
