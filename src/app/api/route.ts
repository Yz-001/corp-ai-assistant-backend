import { success } from '@/lib/api'

export async function GET() {
  return success({ message: 'AI Enterprise Assistant API v1', docs: '/api/v1/health' })
}
