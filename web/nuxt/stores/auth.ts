import { defineStore } from 'pinia'

export type AuthUser = { id: string; email: string; display_name: string }

const cookieBase = {
  sameSite: 'lax' as const,
  path: '/',
}

export const useAuthStore = defineStore('auth', () => {
  const token = useCookie<string | null>('vocko_at', {
    default: () => null,
    maxAge: 60 * 60 * 12,
    ...cookieBase,
  })
  const refreshToken = useCookie<string | null>('vocko_rt', {
    default: () => null,
    maxAge: 60 * 60 * 24 * 14,
    ...cookieBase,
  })
  const user = useCookie<AuthUser | null>('vocko_user', {
    default: () => null,
    maxAge: 60 * 60 * 24 * 14,
    ...cookieBase,
  })

  async function login(email: string, password: string) {
    const config = useRuntimeConfig()
    const data = await $fetch<{
      access_token: string
      refresh_token: string
      user: AuthUser
    }>(`${config.public.apiBase}/auth/signin`, {
      method: 'POST',
      body: { email, password },
    })
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
  }

  async function register(email: string, password: string, display_name: string) {
    const config = useRuntimeConfig()
    const data = await $fetch<{
      access_token: string
      refresh_token: string
      user: AuthUser
    }>(`${config.public.apiBase}/auth/signup`, {
      method: 'POST',
      body: { email, password, display_name },
    })
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
  }

  async function tryRefresh(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
      const config = useRuntimeConfig()
      const data = await $fetch<{ access_token: string; refresh_token: string }>(
        `${config.public.apiBase}/auth/refresh`,
        { method: 'POST', body: { refresh_token: refreshToken.value } },
      )
      token.value = data.access_token
      refreshToken.value = data.refresh_token
      return true
    } catch {
      logout()
      return false
    }
  }

  return { token, refreshToken, user, login, register, logout, tryRefresh }
})
