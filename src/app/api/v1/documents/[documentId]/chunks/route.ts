import { NextRequest } from 'next/server'
import { success, ERR, requireAuth, withErrorHandler, paginateQuery, parsePage } from '@/lib/api'
import { db } from '@/lib/db'

export const GET = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ documentId: string }> }) => {
  const user = await requireAuth()
  const { documentId } = await params

  const doc = await db.document.findUnique({ where: { id: documentId } })
  if (!doc) return ERR.NOT_FOUND('文档不存在')

  if (user.role !== 'super_admin' && doc.tenantId !== user.tenantId) {
    return ERR.FORBIDDEN()
  }

  const sp = req.nextUrl.searchParams
  const { pageNum, pageSize } = parsePage(sp)

  const result = await paginateQuery('DocumentChunk', { documentId }, pageNum, pageSize, { chunkIndex: 'asc' })

  return success(result)
})
