<template>
  <button
    type="button"
    class="w-full rounded-xl border border-slate-700 bg-slate-900/60 p-8 text-left transition hover:border-emerald-700/60 focus:outline-none focus:ring-1 focus:ring-emerald-500"
    @click="$emit('flip')"
  >
    <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
      {{ showBack ? 'Back' : 'Front' }}
    </p>
    <div
      class="simple-card-html mt-3 prose prose-invert prose-sm max-w-none text-lg text-white sm:prose-base sm:text-xl"
      v-html="displayHtml"
    />
    <p class="mt-6 text-xs text-slate-500">
      {{ showBack ? 'Tap to hide answer' : 'Tap to show answer' }}
    </p>
  </button>
</template>

<script setup lang="ts">
import { sanitizeRichHtml } from '~/utils/sanitizeRichHtml'
import { htmlToPlainText } from '~/utils/richText'

const props = defineProps<{
  front: string
  back: string
  showBack: boolean
}>()
defineEmits<{ flip: [] }>()

const displayHtml = computed(() => {
  const raw = props.showBack ? props.back : props.front
  const clean = sanitizeRichHtml(raw)
  if (clean.includes('<')) return clean
  // Legacy plain-text cards
  return htmlToPlainText(raw)
    ? `<p class="whitespace-pre-wrap">${escapeText(raw)}</p>`
    : '<p></p>'
})

function escapeText(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}
</script>

<style scoped>
:deep(.simple-card-html p) {
  margin: 0.25rem 0;
}
:deep(.simple-card-html ul),
:deep(.simple-card-html ol) {
  margin: 0.35rem 0;
  padding-left: 1.25rem;
}
</style>
