<template>
  <div class="mx-auto max-w-xl animate-in fade-in text-center">
    <h1 class="text-3xl font-bold text-white sm:text-4xl">VocKO</h1>
    <p class="mt-3 text-slate-400">Vocabulary learning with flashcards and spaced repetition.</p>
    <div class="mt-8 flex flex-wrap justify-center gap-3">
      <NuxtLink
        v-if="!auth.token"
        to="/register"
        class="rounded-lg bg-emerald-600 px-5 py-2.5 font-medium text-white hover:bg-emerald-500"
      >
        Get started
      </NuxtLink>
      <NuxtLink
        :to="auth.token ? '/deck' : '/login'"
        class="rounded-lg border border-slate-600 px-5 py-2.5 font-medium text-slate-200 hover:border-slate-500"
      >
        {{ auth.token ? 'Your decks' : 'Log in' }}
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
const auth = useAuthStore()
</script>

<style scoped>
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(0.5rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.animate-in.fade-in {
  animation: fade-in 0.35s ease-out both;
}
</style>
