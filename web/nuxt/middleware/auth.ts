export default defineNuxtRouteMiddleware(() => {
  const auth = useAuthStore()
  const t = auth.token
  if (t === null || t === undefined || t === '') {
    return navigateTo('/login')
  }
})
