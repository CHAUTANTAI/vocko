<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header
      class="border-b border-slate-800 bg-slate-900/80 backdrop-blur supports-[backdrop-filter]:bg-slate-900/60"
    >
      <div class="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <NuxtLink to="/" class="flex items-center gap-2 font-semibold tracking-tight text-emerald-400">
          <BookOpen class="h-6 w-6" aria-hidden="true" />
          VocKO
        </NuxtLink>
        <nav class="flex items-center gap-3 text-sm">
          <template v-if="auth.token">
            <NuxtLink
              to="/deck"
              class="rounded-md px-2 py-1 text-slate-300 hover:bg-slate-800 hover:text-white"
            >
              Decks
            </NuxtLink>
            <span class="max-w-[10rem] truncate text-slate-500">{{ auth.user?.display_name }}</span>
            <button
              type="button"
              class="inline-flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-slate-300 hover:border-slate-600 hover:text-white"
              @click="onLogout"
            >
              <LogOut class="h-4 w-4" />
              Log out
            </button>
          </template>
          <template v-else>
            <NuxtLink
              to="/login"
              class="rounded-md px-2 py-1 text-slate-300 hover:bg-slate-800 hover:text-white"
            >
              Log in
            </NuxtLink>
            <NuxtLink
              to="/register"
              class="rounded-md bg-emerald-600 px-3 py-1.5 font-medium text-white hover:bg-emerald-500"
            >
              Register
            </NuxtLink>
          </template>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-5xl px-4 py-8">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { BookOpen, LogOut } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()

function onLogout() {
  auth.logout()
  router.push('/login')
}
</script>
