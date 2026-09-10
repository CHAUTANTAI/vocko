export default defineNuxtRouteMiddleware(async () => {
  const auth = useAuthStore()
  if (auth.token) {
    return navigateTo('/deck')
  }
  if (auth.refreshToken) {
    const ok = await auth.tryRefresh()
    if (ok) return navigateTo('/deck')
  }
})
