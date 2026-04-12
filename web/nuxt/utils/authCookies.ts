import { parse, serialize } from 'cookie-es'

/** Must match server `REFRESH_TOKEN_EXPIRE_DAYS` / `REFRESH_TOKEN_EXPIRE_DAYS_SHORT`. */
export const REFRESH_DAYS_LONG = 30
export const REFRESH_DAYS_SHORT = 7

const ACCESS_MAX_AGE_SEC = 60 * 60 * 12

const COOKIE_OPTS = { path: '/', sameSite: 'lax' as const }

export type AuthUserPayload = { id: string; email: string; display_name: string }

export function readRememberFlag(): boolean {
  if (!import.meta.client) return true
  const raw = parse(document.cookie).vocko_rm
  if (raw === undefined || raw === null) return true
  return String(raw) !== '0'
}

export function writeAuthCookies(
  accessToken: string,
  refreshToken: string,
  user: AuthUserPayload,
  remember: boolean,
): void {
  if (!import.meta.client) return
  const rtDays = remember ? REFRESH_DAYS_LONG : REFRESH_DAYS_SHORT
  const rtMaxAge = 60 * 60 * 24 * rtDays
  const rm = remember ? '1' : '0'
  const chunks = [
    serialize('vocko_at', accessToken, { ...COOKIE_OPTS, maxAge: ACCESS_MAX_AGE_SEC }),
    serialize('vocko_rt', refreshToken, { ...COOKIE_OPTS, maxAge: rtMaxAge }),
    serialize('vocko_user', JSON.stringify(user), { ...COOKIE_OPTS, maxAge: rtMaxAge }),
    serialize('vocko_rm', rm, { ...COOKIE_OPTS, maxAge: rtMaxAge }),
  ]
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
