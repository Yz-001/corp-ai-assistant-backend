import { createHash, randomBytes } from 'crypto'

// 密码哈希
export function hashPassword(password: string): string {
  const salt = randomBytes(16).toString('hex')
  const hash = createHash('sha256').update(salt + password).digest('hex')
  return `${salt}:${hash}`
}

// 验证密码
export function verifyPassword(password: string, stored: string): boolean {
  const [salt, hash] = stored.split(':')
  const verify = createHash('sha256').update(salt + password).digest('hex')
  return verify === hash
}
