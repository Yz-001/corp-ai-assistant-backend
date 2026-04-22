import { NextRequest } from 'next/server'
import { success, ERR, generateToken, withErrorHandler, handleAuthError } from '@/lib/api'
import { db } from '@/lib/db'

export const POST = withErrorHandler(async (req: NextRequest) => {
  const body = await req.json()
  const { refreshToken } = body

  if (!refreshToken) {
    return ERR.BAD_REQUEST('refreshToken 不能为空')
  }

  try {
    // 解析 token: base64(userId:tenantId:role:username:timestamp)
    const decoded = Buffer.from(refreshToken, 'base64').toString('utf-8')
    const [userId, tenantId, role, username, ts] = decoded.split(':')

    if (!userId || !tenantId || !role || !username) {
      return ERR.UNAUTHORIZED()
    }

    // 检查 token 时效
    if (ts && Date.now() - Number(ts) > 7 * 24 * 3600 * 1000) {
      return ERR.UNAUTHORIZED()
    }

    // 验证用户仍然有效
    const user = await db.user.findFirst({
      where: { id: userId, status: 'enabled' },
    })

    if (!user) {
      return ERR.UNAUTHORIZED()
    }

    // 生成新 token
    const accessToken = generateToken(user)
    const expiresIn = 7 * 24 * 3600

    return success({ accessToken, expiresIn })
  } catch {
    return ERR.UNAUTHORIZED()
  }
})
