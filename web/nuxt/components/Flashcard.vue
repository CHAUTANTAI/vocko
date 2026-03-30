<template>
  <div
    v-motion
    class="cursor-pointer select-none rounded-xl border border-slate-600 bg-slate-900 p-8 text-center shadow-md transition-colors hover:border-emerald-600/50"
    :initial="{ rotateY: 0 }"
    :hover="{ scale: 1.01 }"
    @click="flipped = !flipped"
  >
    <p class="text-xs uppercase tracking-wide text-slate-500">{{ flipped ? 'Back' : 'Front' }}</p>
    <p class="mt-3 text-lg text-white">{{ flipped ? back : front }}</p>
    <p class="mt-4 text-xs text-slate-500">Click to flip</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  front: string
  back: string
}>()

const flipped = ref(false)
</script>
