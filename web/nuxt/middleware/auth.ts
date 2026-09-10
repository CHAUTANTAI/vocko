export default defineNuxtRouteMiddleware(async () => {
  const auth = useAuthStore()
  if (auth.token) return
  // Access cookie may be gone while refresh (remember-me) is still valid.
  if (auth.refreshToken) {
    const ok = await auth.tryRefresh()
    if (ok) return
  }
  return navigateTo('/login')
})
