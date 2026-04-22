# Worklog - Task 3-c, 3-d, 3-e

## Task 3-c: Documents Module API Routes

### Files Created:
1. `src/app/api/v1/documents/upload/route.ts` — POST /api/v1/documents/upload
   - Accepts multipart/form-data with file, visibility, tenantId (super_admin only), remark
   - Saves file to /home/z/my-project/data/uploads/ with timestamp prefix
   - Creates Document record with status='pending', then simulates processing → 'completed'
   - Returns { documentId, status }

2. `src/app/api/v1/documents/route.ts` — GET /api/v1/documents
   - Query: pageNum, pageSize, keyword, status, tenantId, visibility, fileType
   - tenant_admin sees own tenant docs; super_admin sees all; regular users see public docs only
   - Uses paginateQuery for consistent pagination

3. `src/app/api/v1/documents/[documentId]/route.ts` — GET & DELETE
   - GET: Returns document detail with chunks
   - DELETE: Deletes document and related DocumentChunks
   - Access control: tenant_admin only own tenant, super_admin all

4. `src/app/api/v1/documents/[documentId]/retry/route.ts` — POST retry parsing
   - Resets status to 'pending', then simulates → 'completed'

5. `src/app/api/v1/documents/[documentId]/reindex/route.ts` — POST rebuild index
   - Deletes existing chunks, resets status, simulates → 'completed'

6. `src/app/api/v1/documents/[documentId]/chunks/route.ts` — GET document chunks
   - Paginated, ordered by chunkIndex asc

## Task 3-d: Admin Tenants Module API Routes

### Files Created:
1. `src/app/api/v1/admin/tenants/route.ts` — GET & POST
   - GET: List tenants (super_admin only) with aggregated userCount, documentCount, requestCount, tokenCount
   - POST: Create tenant with name, code, type, planType, status, quotaConfig

2. `src/app/api/v1/admin/tenants/[tenantId]/route.ts` — GET & PUT
   - GET: Tenant detail with aggregated counts
   - PUT: Update tenant fields (name, type, planType, quotaConfig, configJson)

3. `src/app/api/v1/admin/tenants/[tenantId]/status/route.ts` — PATCH enable/disable
   - Body: { status: "enabled" | "disabled" }

4. `src/app/api/v1/admin/tenants/[tenantId]/usage/route.ts` — GET usage stats
   - Query: dateType (7d|30d)
   - Aggregates from UsageRecord: totals, byService, byDate

5. `src/app/api/v1/admin/tenants/[tenantId]/tools/route.ts` — GET tool permissions
   - Lists all enabled ToolDefinitions with tenant's permission status

6. `src/app/api/v1/admin/tenants/[tenantId]/tools/[toolId]/route.ts` — PUT tool permission
   - Upserts TenantToolPermission with enabled and config

## Task 3-e: Admin Logs Module API Routes

### Files Created:
1. `src/app/api/v1/admin/logs/qa/route.ts` — GET list QA logs
   - Query: pageNum, pageSize, tenantId, userId, status, keyword, startTime, endTime
   - Enriches with user and tenant info

2. `src/app/api/v1/admin/logs/qa/[logId]/route.ts` — GET QA log detail
   - Includes user and tenant info

3. `src/app/api/v1/admin/logs/tools/route.ts` — GET list tool call logs
   - Query: pageNum, pageSize, tenantId, toolId, status, keyword, startTime, endTime

4. `src/app/api/v1/admin/logs/tools/[logId]/route.ts` — GET tool call log detail

5. `src/app/api/v1/admin/logs/audit/route.ts` — GET list audit logs
   - Query: pageNum, pageSize, tenantId, module, action, startTime, endTime
   - Fixed lint issue: renamed `module` variable to `moduleFilter` to avoid Next.js reserved name conflict

6. `src/app/api/v1/admin/logs/export/route.ts` — GET export logs
   - Query: type (qa|tools|audit), startTime, endTime
   - Returns JSON array for now

## Implementation Notes:
- All routes use `withErrorHandler()` wrapper for consistent error handling
- Auth guards use `requireAuth()`, `requireAdmin()`, `requireSuperAdmin()` with proper error handling
- Next.js 16 params pattern: `async (req, { params }: { params: Promise<{...}> })` with `await params`
- Tenant isolation enforced: tenant_admin only sees own tenant data
- Lint passes cleanly with no errors
