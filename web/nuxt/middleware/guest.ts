export default defineNuxtRouteMiddleware(() => {
  const auth = useAuthStore()
  const t = auth.token
  if (t) {
    return navigateTo('/deck')
  }
})
