import { headers } from 'next/headers'
import { db } from '@/lib/db'
import { ERR } from './response'

export interface AuthUser {
  userId: string
  tenantId: string
  role: string
  username: string
}

// 从请求头获取当前用户（简易 JWT 方案）
export async function getAuthUser(): Promise<AuthUser | null> {
  const h = await headers()
  const auth = h.get('authorization')
  if (!auth?.startsWith('Bearer ')) return null

  const token = auth.slice(7)
  try {
    // 简易 token 解析: base64(userId:tenantId:role:username:timestamp)
    const decoded = Buffer.from(token, 'base64').toString('utf-8')
    const [userId, tenantId, role, username, ts] = decoded.split(':')
    if (!userId || !tenantId || !role) return null

    // 检查 token 时效（7天）
    if (ts && Date.now() - Number(ts) > 7 * 24 * 3600 * 1000) return null

    // 验证用户存在且启用
    const user = await db.user.findFirst({ where: { id: userId, status: 'enabled' } })
    if (!user) return null

    return { userId, tenantId, role, username }
  } catch {
    return null
  }
}

// 生成 token
export function generateToken(user: { id: string; tenantId: string; role: string; username: string }): string {
  const raw = `${user.id}:${user.tenantId}:${user.role}:${user.username}:${Date.now()}`
  return Buffer.from(raw).toString('base64')
}

// 需要登录的守卫
export async function requireAuth(): Promise<AuthUser> {
  const user = await getAuthUser()
  if (!user) throw new Error('UNAUTHORIZED')
  return user
}

// 需要管理员权限的守卫
export async function requireAdmin(): Promise<AuthUser> {
  const user = await requireAuth()
  if (!['super_admin', 'tenant_admin'].includes(user.role)) throw new Error('FORBIDDEN')
  return user
}

// 需要超级管理员权限的守卫
export async function requireSuperAdmin(): Promise<AuthUser> {
  const user = await requireAuth()
  if (user.role !== 'super_admin') throw new Error('FORBIDDEN')
  return user
}

// 将守卫错误转为 Response
export function handleAuthError(e: unknown) {
  if (e instanceof Error) {
    if (e.message === 'UNAUTHORIZED') return ERR.UNAUTHORIZED()
    if (e.message === 'FORBIDDEN') return ERR.FORBIDDEN()
  }
  return null
}
