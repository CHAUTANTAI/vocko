import DOMPurify from 'isomorphic-dompurify'

export function sanitizeRichHtml(html: string | undefined | null): string {
  if (!html) return ''
  return DOMPurify.sanitize(html, { USE_PROFILES: { html: true } })
}
