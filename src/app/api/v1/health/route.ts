import { success } from '@/lib/api'
import { db } from '@/lib/db'

// GET /api/v1/health
export async function GET() {
  try {
    await db.$queryRaw`SELECT 1`
    return success({ status: 'ok', timestamp: new Date().toISOString(), database: 'connected' })
  } catch {
    return success({ status: 'degraded', timestamp: new Date().toISOString(), database: 'disconnected' })
  }
}
