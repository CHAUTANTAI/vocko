<template>
  <button
    type="button"
    class="w-full rounded-xl border border-slate-700 bg-slate-900/60 p-8 text-left transition hover:border-emerald-700/60 focus:outline-none focus:ring-1 focus:ring-emerald-500"
    @click="$emit('flip')"
  >
    <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
      {{ showBack ? 'Back' : 'Front' }}
    </p>
    <p class="mt-3 whitespace-pre-wrap text-lg text-white sm:text-xl">
      {{ showBack ? back : front }}
    </p>
    <p class="mt-6 text-xs text-slate-500">
      {{ showBack ? 'Tap to hide answer' : 'Tap to show answer' }}
    </p>
  </button>
</template>

<script setup lang="ts">
defineProps<{
  front: string
  back: string
  showBack: boolean
}>()
defineEmits<{ flip: [] }>()
</script>
