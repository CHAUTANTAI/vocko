import { defineStore } from 'pinia'
import { useStorage } from '@vueuse/core'

export type AuthUser = { id: string; email: string; display_name: string }

export const useAuthStore = defineStore('auth', () => {
  const token = useStorage('vocko_at', '')
  const refreshToken = useStorage('vocko_rt', '')
  const user = useStorage<AuthUser | null>('vocko_user', null)

  const config = useRuntimeConfig()

  async function login(email: string, password: string) {
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
    token.value = ''
    refreshToken.value = ''
    user.value = null
  }

  async function tryRefresh(): Promise<boolean> {
    if (!refreshToken.value) return false
    try {
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
