/**
 * SSR-safe HTML cleanup for rich text (TipTap output).
 * Avoids isomorphic-dompurify/jsdom on Windows Node (ESM loader rejects absolute `c:\` import URLs).
 * Stronger than nothing: strips scripts, styles, inline handlers, javascript: URLs.
 */
function roughSanitizeHtml(html: string): string {
  let s = html
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?>[\s\S]*?<\/style>/gi, '')
    .replace(/\sjavascript:/gi, ' blocked:')
    .replace(/\son\w+\s*=/gi, ' data-removed=')
  s = s.replace(/href\s*=\s*(["'])\s*javascript:/gi, 'href=$1blocked:')
  return s
}

export function sanitizeRichHtml(html: string | undefined | null): string {
  if (!html) return ''
  return roughSanitizeHtml(html)
}
