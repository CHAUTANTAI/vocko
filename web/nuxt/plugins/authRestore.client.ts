/**
 * Restore session on load when access cookie is missing/expired but refresh remains
 * (typical after closing the browser overnight with Remember me).
 */
export default defineNuxtPlugin(async () => {
  if (!import.meta.client) return
  const auth = useAuthStore()
  if (!auth.token && auth.refreshToken) {
    await auth.tryRefresh()
  }
})
