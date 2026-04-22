import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// PUT /api/v1/admin/tools/[toolId] - Update tool
export const PUT = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ toolId: string }> }) => {
  await requireAdmin()
  const { toolId } = await params
  const { name, type, description, config } = await req.json()

  const tool = await db.toolDefinition.findUnique({ where: { id: toolId } })
  if (!tool) return ERR.NOT_FOUND('工具不存在')

  const updated = await db.toolDefinition.update({
    where: { id: toolId },
    data: {
      ...(name !== undefined && { name }),
      ...(type !== undefined && { type }),
      ...(description !== undefined && { description }),
      ...(config !== undefined && { configJson: JSON.stringify(config) }),
    },
  })
  return success(updated)
})
