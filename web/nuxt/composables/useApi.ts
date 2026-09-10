import { touchApiActivity } from '~/utils/apiActivity'

export function useApi() {
  const config = useRuntimeConfig()
  const auth = useAuthStore()

  async function api<T>(url: string, opts: Record<string, unknown> = {}) {
    const headers: Record<string, string> = {
      ...((opts.headers as Record<string, string>) || {}),
    }
    if (auth.token) headers.Authorization = `Bearer ${auth.token}`

    const exec = () =>
      $fetch<T>(url, {
        baseURL: config.public.apiBase as string,
        ...opts,
        headers,
      })

    touchApiActivity()
    try {
      const data = await exec()
      touchApiActivity()
      return data
    } catch (err: unknown) {
      const e = err as { statusCode?: number; status?: number }
      const code = e.statusCode ?? e.status
      if (code === 401 && auth.refreshToken) {
        const ok = await auth.tryRefresh()
        if (ok) {
          const h2 = { ...((opts.headers as Record<string, string>) || {}) }
          if (auth.token) h2.Authorization = `Bearer ${auth.token}`
          touchApiActivity()
          const data = await $fetch<T>(url, {
            baseURL: config.public.apiBase as string,
            ...opts,
            headers: h2,
          })
          touchApiActivity()
          return data
        }
      }
      throw err
    }
  }

  return { api }
}
