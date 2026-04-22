import { NextRequest } from 'next/server'
import { success, ERR, requireAuth, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

export const POST = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ documentId: string }> }) => {
  const user = await requireAuth()
  const { documentId } = await params

  const doc = await db.document.findUnique({ where: { id: documentId } })
  if (!doc) return ERR.NOT_FOUND('文档不存在')

  if (user.role !== 'super_admin' && doc.tenantId !== user.tenantId) {
    return ERR.FORBIDDEN()
  }

  // Reset to pending, then simulate processing → completed
  await db.document.update({
    where: { id: documentId },
    data: { status: 'pending', errorMessage: null },
  })

  // Simulate async processing
  await db.document.update({
    where: { id: documentId },
    data: { status: 'completed', chunkCount: 0 },
  })

  return success({ documentId, status: 'completed' }, '重试解析成功')
})
