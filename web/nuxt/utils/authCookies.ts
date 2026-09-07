import { parse, serialize } from 'cookie-es'

/** Must match server `REFRESH_TOKEN_EXPIRE_DAYS` when remember is on. */
export const REFRESH_DAYS_LONG = 30

/**
 * Access JWT is short-lived (server ~15m); cookie only needs to survive until refresh.
 * Keep a modest persistent max-age when remember=true so the jar stays coherent.
 */
const ACCESS_MAX_AGE_SEC = 60 * 60 * 12

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
  const rtMaxAge = 60 * 60 * 24 * REFRESH_DAYS_LONG
  const rm = remember ? '1' : '0'
  const chunks = [
    serialize('vocko_at', accessToken, persistOpts(remember, ACCESS_MAX_AGE_SEC)),
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
