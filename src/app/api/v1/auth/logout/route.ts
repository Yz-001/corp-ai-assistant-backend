import { NextRequest } from 'next/server'
import { success, requireAuth, withErrorHandler } from '@/lib/api'

export const POST = withErrorHandler(async (req: NextRequest) => {
  await requireAuth()

  // 无状态 JWT，服务端不需要额外处理
  return success(null, '退出登录成功')
})
