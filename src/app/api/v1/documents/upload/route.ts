import { NextRequest } from 'next/server'
import { writeFile, mkdir } from 'fs/promises'
import path from 'path'
import { success, fail, ERR, requireAuth, withErrorHandler } from '@/lib/api'
import { db } from '@/lib/db'

const UPLOAD_DIR = '/home/z/my-project/data/uploads'

export const POST = withErrorHandler(async (req: NextRequest) => {
  const user = await requireAuth()

  const formData = await req.formData()
  const file = formData.get('file') as File | null
  const visibility = (formData.get('visibility') as string) || 'private'
  const remark = formData.get('remark') as string | null
  let tenantId = user.tenantId

  // super_admin can specify tenantId
  if (formData.get('tenantId')) {
    if (user.role !== 'super_admin') return ERR.FORBIDDEN()
    tenantId = formData.get('tenantId') as string
  }

  if (!file) return fail(4001, '缺少文件', 400)
  if (!['public', 'private'].includes(visibility)) return fail(4001, 'visibility 必须为 public 或 private', 400)

  // Ensure upload dir exists
  await mkdir(UPLOAD_DIR, { recursive: true })

  // Derive file type from extension
  const ext = path.extname(file.name).slice(1).toLowerCase()
  const allowedTypes = ['pdf', 'docx', 'txt', 'md', 'doc', 'csv', 'xlsx']
  const fileType = allowedTypes.includes(ext) ? ext : 'txt'

  // Save file to disk
  const timestamp = Date.now()
  const storageName = `${timestamp}-${file.name}`
  const storagePath = path.join(UPLOAD_DIR, storageName)
  const buffer = Buffer.from(await file.arrayBuffer())
  await writeFile(storagePath, buffer)

  // Create document record
  const doc = await db.document.create({
    data: {
      tenantId,
      name: file.name,
      fileName: file.name,
      fileType,
      fileSize: file.size,
      storagePath,
      visibility,
      status: 'pending',
      chunkCount: 0,
      createdBy: user.userId,
      errorMessage: remark || null,
    },
  })

  // Simulate processing: set to completed
  await db.document.update({
    where: { id: doc.id },
    data: { status: 'completed', chunkCount: 0 },
  })

  return success({ documentId: doc.id, status: 'completed' })
})
