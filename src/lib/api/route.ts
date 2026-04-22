import { NextRequest, NextResponse } from 'next/server'
import { handleAuthError } from './auth'
import { ERR } from './response'

// 统一路由错误处理包装器
export function withErrorHandler(handler: (req: NextRequest, ctx?: any) => Promise<NextResponse>) {
  return async (req: NextRequest, ctx?: any): Promise<NextResponse> => {
    try {
      return await handler(req, ctx)
    } catch (e: any) {
      // 先尝试处理认证错误
      const authErr = handleAuthError(e)
      if (authErr) return authErr

      // 通用错误
      console.error(`[API Error] ${req.method} ${req.url}:`, e.message)
      return ERR.SERVER_ERROR(e.message || '服务器内部错误')
    }
  }
}
