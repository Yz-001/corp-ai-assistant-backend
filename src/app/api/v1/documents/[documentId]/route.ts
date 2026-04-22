import { NextRequest } from 'next/server'
import { success, ERR, requireAuth, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ documentId: string }> }) => {
  const user = await requireAuth()
  const { documentId } = await params

  const doc = await db.document.findUnique({ where: { id: documentId }, include: { chunks: true } })
  if (!doc) return ERR.NOT_FOUND('文档不存在')

  // Access check: tenant_admin sees own tenant, super_admin sees all
  if (user.role !== 'super_admin' && doc.tenantId !== user.tenantId) {
    return ERR.FORBIDDEN()
  }

  return success(doc)
})

export const DELETE = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ documentId: string }> }) => {
  const user = await requireAuth()
  const { documentId } = await params

  const doc = await db.document.findUnique({ where: { id: documentId } })
  if (!doc) return ERR.NOT_FOUND('文档不存在')

  // Access check
  if (user.role !== 'super_admin' && doc.tenantId !== user.tenantId) {
    return ERR.FORBIDDEN()
  }

  // Delete related chunks first, then document
  await db.documentChunk.deleteMany({ where: { documentId } })
  await db.document.delete({ where: { id: documentId } })

  return success(null, '删除成功')
})
