import { NextRequest } from 'next/server'
import { withErrorHandler, requireAdmin, success, ERR, db } from '@/lib/api'

// PUT /api/v1/admin/mcp/tools/[toolId]/bind-tenants
export const PUT = withErrorHandler(async (req: NextRequest, { params }: { params: Promise<{ toolId: string }> }) => {
  await requireAdmin()
  const { toolId } = await params
  const { tenantIds } = await req.json()
  if (!Array.isArray(tenantIds)) return ERR.BAD_REQUEST('tenantIds 必须为数组')

  const mcpTool = await db.mcpTool.findUnique({ where: { id: toolId } })
  if (!mcpTool) return ERR.NOT_FOUND('MCP工具不存在')

  // Find or create a ToolDefinition for this MCP tool
  let toolDef = await db.toolDefinition.findUnique({ where: { code: `mcp_${mcpTool.toolCode}` } })
  if (!toolDef) {
    toolDef = await db.toolDefinition.create({
      data: {
        code: `mcp_${mcpTool.toolCode}`,
        name: mcpTool.toolName,
        type: 'mcp_tool',
        description: mcpTool.description,
        configJson: JSON.stringify({ serverId: mcpTool.serverId, toolCode: mcpTool.toolCode }),
      },
    })
  }

  // Upsert tenant tool permissions
  for (const tenantId of tenantIds) {
    await db.tenantToolPermission.upsert({
      where: { tenantId_toolId: { tenantId, toolId: toolDef.id } },
      update: { enabled: true },
      create: { tenantId, toolId: toolDef.id, enabled: true },
    })
  }

  // Disable permissions for tenants not in the list
  const existingPerms = await db.tenantToolPermission.findMany({ where: { toolId: toolDef.id } })
  for (const perm of existingPerms) {
    if (!tenantIds.includes(perm.tenantId)) {
      await db.tenantToolPermission.update({ where: { id: perm.id }, data: { enabled: false } })
    }
  }

  return success(null, '租户绑定更新成功')
})
