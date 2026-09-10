/** Last time the browser talked to the API (any request, including /health). */
let lastApiActivityAt = Date.now()

export function touchApiActivity(): void {
  lastApiActivityAt = Date.now()
}

export function getLastApiActivityAt(): number {
  return lastApiActivityAt
}

/** Idle gap before FE pings /health to reduce Render free cold starts (~15m spin-down). */
export const API_KEEPALIVE_IDLE_MS = 10 * 60 * 1000

/** How often to check whether a keep-alive ping is due. */
export const API_KEEPALIVE_CHECK_MS = 30 * 1000
