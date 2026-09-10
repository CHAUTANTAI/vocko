import { parse, serialize } from 'cookie-es'

/** Must match server `REFRESH_TOKEN_EXPIRE_DAYS` when remember is on. */
export const REFRESH_DAYS_LONG = 30

const COOKIE_OPTS = { path: '/', sameSite: 'lax' as const }

export type AuthUserPayload = { id: string; email: string; display_name: string }

export function readRememberFlag(): boolean {
  if (!import.meta.client) return true
  const raw = parse(document.cookie).vocko_rm
  if (raw === undefined || raw === null || raw === '') return true
  return String(raw) !== '0'
}

function persistOpts(remember: boolean, maxAgeSec: number) {
  // Session cookie when not remembering — expires when the browser closes.
  return remember ? { ...COOKIE_OPTS, maxAge: maxAgeSec } : { ...COOKIE_OPTS }
}

export function writeAuthCookies(
  accessToken: string,
  refreshToken: string,
  user: AuthUserPayload | null | undefined,
  remember: boolean,
): void {
  if (!import.meta.client) return
  // Keep access cookie in the jar as long as refresh when remembering, so returning
  // after >12h still has auth cookies (JWT may be expired; middleware/API will refresh).
  const rtMaxAge = 60 * 60 * 24 * REFRESH_DAYS_LONG
  const atMaxAge = remember ? rtMaxAge : 60 * 60 * 12
  const rm = remember ? '1' : '0'
  const chunks = [
    serialize('vocko_at', accessToken, persistOpts(remember, atMaxAge)),
    serialize('vocko_rt', refreshToken, persistOpts(remember, rtMaxAge)),
    serialize('vocko_rm', rm, persistOpts(remember, rtMaxAge)),
  ]
  if (user) {
    chunks.push(serialize('vocko_user', JSON.stringify(user), persistOpts(remember, rtMaxAge)))
  }
  for (const c of chunks) {
    document.cookie = c
  }
}

export function clearAuthCookies(): void {
  if (!import.meta.client) return
  for (const name of ['vocko_at', 'vocko_rt', 'vocko_user', 'vocko_rm']) {
    document.cookie = serialize(name, '', { ...COOKIE_OPTS, maxAge: -1 })
  }
}
