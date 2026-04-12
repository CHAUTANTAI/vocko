import { defineStore } from 'pinia'
import { clearAuthCookies, readRememberFlag, writeAuthCookies } from '~/utils/authCookies'

export type AuthUser = { id: string; email: string; display_name: string }

const cookieBase = {
  sameSite: 'lax' as const,
  path: '/',
  watch: false as const,
}

export const useAuthStore = defineStore('auth', () => {
  const token = useCookie<string | null>('vocko_at', {
    default: () => null,
    ...cookieBase,
  })
  const refreshToken = useCookie<string | null>('vocko_rt', {
    default: () => null,
    ...cookieBase,
  })
  const user = useCookie<AuthUser | null>('vocko_user', {
    default: () => null,
    ...cookieBase,
  })

  async function login(email: string, password: string, remember = true) {
    const config = useRuntimeConfig()
    const data = await $fetch<{
      access_token: string
      refresh_token: string
      user: AuthUser
    }>(`${config.public.apiBase}/auth/signin`, {
      method: 'POST',
      body: { email, password, remember },
    })
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    writeAuthCookies(data.access_token, data.refresh_token, data.user, remember)
  }

  async function register(email: string, password: string, display_name: string, remember = true) {
    const config = useRuntimeConfig()
    const data = await $fetch<{
      access_token: string
      refresh_token: string
      user: AuthUser
    }>(`${config.public.apiBase}/auth/signup`, {
      method: 'POST',
      body: { email, password, display_name, remember },
    })
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    writeAuthCookies(data.access_token, data.refresh_token, data.user, remember)
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    clearAuthCookies()
  }

  async function tryRefresh(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
      const config = useRuntimeConfig()
      const data = await $fetch<{ access_token: string; refresh_token: string }>(
        `${config.public.apiBase}/auth/refresh`,
        { method: 'POST', body: { refresh_token: refreshToken.value } },
      )
      const remember = readRememberFlag()
      token.value = data.access_token
      refreshToken.value = data.refresh_token
      if (user.value) {
        writeAuthCookies(data.access_token, data.refresh_token, user.value, remember)
      }
      return true
    } catch {
      logout()
      return false
    }
  }

  return { token, refreshToken, user, login, register, logout, tryRefresh }
})
