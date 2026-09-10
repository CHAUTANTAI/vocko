import {
  API_KEEPALIVE_CHECK_MS,
  API_KEEPALIVE_IDLE_MS,
  getLastApiActivityAt,
  touchApiActivity,
} from '~/utils/apiActivity'

/**
 * While the tab is open: if no API traffic for 10 minutes, hit GET /health once.
 * Keeps Render free web process warm (~15m idle spin-down). Does nothing when the tab is closed.
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const config = useRuntimeConfig()
  let inFlight = false

  async function pingHealth() {
    if (inFlight) return
    inFlight = true
    touchApiActivity()
    try {
      await $fetch('/health', {
        baseURL: config.public.apiBase as string,
        timeout: 20_000,
      })
    } catch {
      // Ignore — cold start or network; next check will retry after another idle window.
    } finally {
      touchApiActivity()
      inFlight = false
    }
  }

  function maybeKeepAlive() {
    if (Date.now() - getLastApiActivityAt() >= API_KEEPALIVE_IDLE_MS) {
      void pingHealth()
    }
  }

  const timer = window.setInterval(maybeKeepAlive, API_KEEPALIVE_CHECK_MS)

  const onVisibility = () => {
    if (document.visibilityState === 'visible') maybeKeepAlive()
  }
  document.addEventListener('visibilitychange', onVisibility)

  if (import.meta.hot) {
    import.meta.hot.dispose(() => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisibility)
    })
  }
})
