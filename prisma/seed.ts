import { db } from '@/lib/db'
import { hashPassword } from '@/lib/api/password'

async function seed() {
  console.log('🌱 Seeding database...')

  // 1. Create tenants
  const tenants = await Promise.all([
    db.tenant.upsert({ where: { code: 'platform' }, update: {}, create: { name: '平台总部', code: 'platform', type: 'public', status: 'enabled', planType: 'enterprise' } }),
    db.tenant.upsert({ where: { code: 'sales_hq' }, update: {}, create: { name: '销售总部', code: 'sales_hq', type: 'sales', status: 'enabled', planType: 'pro' } }),
    db.tenant.upsert({ where: { code: 'partner_east' }, update: {}, create: { name: '华东加盟商', code: 'partner_east', type: 'partner', status: 'enabled', planType: 'pro' } }),
    db.tenant.upsert({ where: { code: 'enterprise_a' }, update: {}, create: { name: '企业客户A', code: 'enterprise_a', type: 'enterprise', status: 'enabled', planType: 'basic' } }),
  ])

  // 2. Create users
  const pw = hashPassword('123456')
  const users = await Promise.all([
    db.user.upsert({ where: { username: 'admin' }, update: {}, create: { username: 'admin', passwordHash: pw, role: 'super_admin', tenantId: tenants[0].id, email: 'admin@example.com', status: 'enabled' } }),
    db.user.upsert({ where: { username: 'sales_admin' }, update: {}, create: { username: 'sales_admin', passwordHash: pw, role: 'tenant_admin', tenantId: tenants[1].id, email: 'sales@example.com', status: 'enabled' } }),
    db.user.upsert({ where: { username: 'sales_user' }, update: {}, create: { username: 'sales_user', passwordHash: pw, role: 'tenant_user', tenantId: tenants[1].id, email: 'salesuser@example.com', status: 'enabled' } }),
    db.user.upsert({ where: { username: 'partner_admin' }, update: {}, create: { username: 'partner_admin', passwordHash: pw, role: 'tenant_admin', tenantId: tenants[2].id, email: 'partner@example.com', status: 'enabled' } }),
    db.user.upsert({ where: { username: 'user_a' }, update: {}, create: { username: 'user_a', passwordHash: pw, role: 'tenant_user', tenantId: tenants[3].id, email: 'usera@example.com', status: 'enabled' } }),
  ])

  // 3. Create prompt configs (global + tenant)
  const globalTenantId = 'global'
  // Ensure a global tenant record for prompt configs
  await db.tenant.upsert({ where: { code: '_global' }, update: {}, create: { id: globalTenantId, name: '全局配置', code: '_global', type: 'public', status: 'enabled' } })

  const tags = ['产品知识', '销售话术', '使用教程', '常见问题', '订单查询', '物流轨迹']
  for (let i = 0; i < tags.length; i++) {
    await db.promptConfig.upsert({
      where: { id: `tag_global_${i}` },
      update: {},
      create: { id: `tag_global_${i}`, tenantId: globalTenantId, scope: 'global', channel: 'web', type: 'tag', title: tags[i], content: tags[i], sortOrder: i, enabled: true },
    })
  }

  const suggestions = [
    '这款产品适合哪些客户？',
    '新员工怎么快速了解产品？',
    '客户问价格高怎么回答？',
    '如何查询订单状态？',
    '售后问题怎么处理？',
    '物流时效一般多久？',
  ]
  for (let i = 0; i < suggestions.length; i++) {
    await db.promptConfig.upsert({
      where: { id: `sug_global_${i}` },
      update: {},
      create: { id: `sug_global_${i}`, tenantId: globalTenantId, scope: 'global', channel: 'web', type: 'suggested_question', title: suggestions[i].slice(0, 10), content: suggestions[i], sortOrder: i, enabled: true },
    })
  }

  // 4. Create tool definitions
  const tools = [
    { code: 'order_query', name: '订单查询', type: 'database_query', description: '按订单号查询订单状态和详情' },
    { code: 'logistics_query', name: '物流轨迹查询', type: 'http_service', description: '查询物流配送轨迹信息' },
    { code: 'crm_query', name: 'CRM客户查询', type: 'internal_api', description: '查询客户CRM信息' },
    { code: 'aftersale_query', name: '售后工单查询', type: 'database_query', description: '查询售后工单状态' },
  ]
  for (const tool of tools) {
    await db.toolDefinition.upsert({ where: { code: tool.code }, update: {}, create: tool })
  }

  // 5. Create some demo chat sessions & messages
  const session1 = await db.chatSession.create({ data: { tenantId: tenants[1].id, userId: users[2].id, title: '产品咨询', channel: 'web', status: 'active' } })
  await db.chatMessage.createMany({
    data: [
      { tenantId: tenants[1].id, sessionId: session1.id, role: 'user', content: '这款产品适合哪些客户？', status: 'done' },
      { tenantId: tenants[1].id, sessionId: session1.id, role: 'assistant', content: '这款产品主要适合中小企业客户，特别是有数字化转型需求的公司。根据销售手册，产品的核心优势在于...', status: 'done', sourcesJson: JSON.stringify([{ documentId: 'demo_doc_1', documentName: '销售手册.pdf', chunkId: 'c_1', chunkIndex: 1, snippet: '适合中小企业客户...', score: 0.93 }]), tokenUsageJson: JSON.stringify({ promptTokens: 200, completionTokens: 120, totalTokens: 320 }) },
    ],
  })

  const session2 = await db.chatSession.create({ data: { tenantId: tenants[1].id, userId: users[2].id, title: '订单问题', channel: 'web', status: 'active' } })
  await db.chatMessage.createMany({
    data: [
      { tenantId: tenants[1].id, sessionId: session2.id, role: 'user', content: '如何查询订单状态？', status: 'done' },
      { tenantId: tenants[1].id, sessionId: session2.id, role: 'assistant', content: '您可以通过订单查询工具来查看订单状态，只需提供订单号即可查询。', status: 'done', tokenUsageJson: JSON.stringify({ promptTokens: 150, completionTokens: 80, totalTokens: 230 }) },
    ],
  })

  // 6. Create demo documents
  await db.document.createMany({
    data: [
      { tenantId: tenants[0].id, name: '销售手册', fileName: '销售手册.pdf', fileType: 'pdf', fileSize: 2048000, storagePath: '/uploads/sales_manual.pdf', visibility: 'public', status: 'completed', chunkCount: 15, createdBy: users[0].id },
      { tenantId: tenants[1].id, name: '产品规格说明', fileName: '产品规格说明.docx', fileType: 'docx', fileSize: 1024000, storagePath: '/uploads/product_spec.docx', visibility: 'private', status: 'completed', chunkCount: 8, createdBy: users[1].id },
      { tenantId: tenants[1].id, name: '售后服务政策', fileName: '售后政策.txt', fileType: 'txt', fileSize: 512000, storagePath: '/uploads/aftersale.txt', visibility: 'private', status: 'pending', createdBy: users[1].id },
    ],
  })

  // 7. Create some QA logs for monitoring
  const now = Date.now()
  const logData = []
  for (let i = 0; i < 50; i++) {
    const hoursAgo = Math.floor(Math.random() * 168) // last 7 days
    logData.push({
      tenantId: tenants[Math.floor(Math.random() * tenants.length)].id,
      userId: users[Math.floor(Math.random() * users.length)].id,
      sessionId: session1.id,
      query: suggestions[Math.floor(Math.random() * suggestions.length)],
      answer: '这是模拟回答内容...',
      modelName: 'placeholder',
      latencyMs: Math.floor(Math.random() * 3000) + 200,
      promptTokens: Math.floor(Math.random() * 500) + 50,
      completionTokens: Math.floor(Math.random() * 300) + 30,
      totalTokens: Math.floor(Math.random() * 800) + 80,
      sourceCount: Math.floor(Math.random() * 5),
      status: Math.random() > 0.05 ? 'success' : 'failed',
      createdAt: new Date(now - hoursAgo * 3600000),
    })
  }
  await db.qaLog.createMany({ data: logData })

  // 8. Create some usage records
  for (let d = 0; d < 7; d++) {
    const date = new Date(now - d * 86400000).toISOString().slice(0, 10)
    for (const tenant of tenants) {
      await db.usageRecord.upsert({
        where: { tenantId_userId_serviceType_statDate: { tenantId: tenant.id, userId: '', serviceType: 'chat', statDate: date } },
        update: { requestCount: Math.floor(Math.random() * 500) + 50, tokenCount: Math.floor(Math.random() * 50000) + 5000 },
        create: { tenantId: tenant.id, serviceType: 'chat', requestCount: Math.floor(Math.random() * 500) + 50, tokenCount: Math.floor(Math.random() * 50000) + 5000, statDate: date },
      })
    }
  }

  // 9. Create MCP server demo
  const mcpServer = await db.mcpServer.create({
    data: { name: '订单系统MCP', baseUrl: 'https://mcp.example.com', authType: 'bearer', authConfigJson: JSON.stringify({ token: 'demo_token' }), status: 'enabled', timeoutSeconds: 20, description: '订单与物流服务', lastCheckStatus: 'unknown' },
  })
  await db.mcpTool.createMany({
    data: [
      { serverId: mcpServer.id, toolCode: 'order_query', toolName: '订单查询', description: '按订单号查询订单', status: 'enabled' },
      { serverId: mcpServer.id, toolCode: 'logistics_query', toolName: '物流查询', description: '查询物流轨迹', status: 'enabled' },
    ],
  })

  console.log('✅ Seed completed!')
  console.log('   Users: admin/admin, sales_admin/123456, sales_user/123456, partner_admin/123456, user_a/123456')
}

seed().catch(e => { console.error('Seed error:', e); process.exit(1) })
