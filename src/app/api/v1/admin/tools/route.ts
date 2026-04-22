import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, paginateQuery, parsePage, db } from '@/lib/api'

// GET /api/v1/admin/tools - List tools
export const GET = withErrorHandler(async (req: NextRequest) => {
  const auth = await requireAdmin()
  const { pageNum, pageSize } = parsePage(req.nextUrl.searchParams)

  const tools = await db.toolDefinition.findMany({
    orderBy: { createdAt: 'desc' },
  })

  // Enrich with stats
  const enriched = await Promise.all(tools.map(async t => {
    const stats = await db.toolCallLog.aggregate({
      _count: true,
      _avg: { latencyMs: true },
      where: { toolId: t.id, status: 'failed' },
    })
    const total = await db.toolCallLog.count({ where: { toolId: t.id } })
    return {
      toolId: t.id,
      code: t.code,
      name: t.name,
      type: t.type,
      description: t.description,
      status: t.status,
      healthStatus: t.healthStatus,
      callCount: total,
      avgLatencyMs: Math.round(stats._avg.latencyMs || 0),
      errorRate: total > 0 ? Number((stats._count / total * 100).toFixed(2)) : 0,
    }
  }))

  const total = enriched.length
  const start = (pageNum - 1) * pageSize
  const list = enriched.slice(start, start + pageSize)

  return success({ list, total, pageNum, pageSize })
})

// POST /api/v1/admin/tools - Create tool
export const POST = withErrorHandler(async (req: NextRequest) => {
  await requireAdmin()
  const { code, name, type, description, config } = await req.json()
  if (!code || !name || !type) return ERR.BAD_REQUEST('code/name/type 必填')

  const existing = await db.toolDefinition.findUnique({ where: { code } })
  if (existing) return ERR.DUPLICATE('工具编码已存在')

  const tool = await db.toolDefinition.create({
    data: { code, name, type, description: description || '', configJson: JSON.stringify(config || {}) },
  })
  return success(tool)
})
