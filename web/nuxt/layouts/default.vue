<template>
  <div class="min-h-screen bg-slate-950 text-slate-100">
    <header
      class="border-b border-slate-800 bg-slate-900/80 backdrop-blur supports-[backdrop-filter]:bg-slate-900/60"
    >
      <div
        class="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:gap-4"
      >
        <div class="flex items-center justify-between gap-4 sm:contents">
          <NuxtLink to="/" class="flex shrink-0 items-center gap-2 font-semibold tracking-tight text-emerald-400 sm:order-1">
            <BookOpen class="h-6 w-6" aria-hidden="true" />
            VocKO
          </NuxtLink>
          <nav class="flex shrink-0 items-center gap-3 text-sm sm:order-3 sm:ml-auto">
            <template v-if="auth.token">
              <NuxtLink
                to="/deck"
                class="rounded-md px-2 py-1 text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                Decks
              </NuxtLink>
              <NuxtLink
                to="/import/toeic-text"
                class="rounded-md px-2 py-1 text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                Import
              </NuxtLink>
              <NuxtLink
                to="/learning/history"
                class="rounded-md px-2 py-1 text-slate-300 hover:bg-slate-800 hover:text-white"
              >
                History
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

        <div
          v-if="auth.token"
          ref="searchRootRef"
          class="relative w-full min-w-0 sm:order-2 sm:mx-0 sm:max-w-md sm:flex-1"
        >
          <div class="relative">
            <Search
              class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
              aria-hidden="true"
            />
            <input
              v-model="searchQuery"
              type="search"
              autocomplete="off"
              aria-label="Search decks and cards"
              :aria-expanded="panelOpen"
              aria-controls="global-search-results"
              class="w-full rounded-lg border border-slate-700 bg-slate-950 py-2 pl-10 pr-3 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="Search decks & card fronts…"
              @focus="onSearchFocus"
              @keydown.escape.prevent="closePanel"
            />
          </div>
          <div
            v-show="panelOpen"
            id="global-search-results"
            class="absolute left-0 right-0 top-full z-50 mt-1 max-h-[min(24rem,70vh)] overflow-y-auto rounded-lg border border-slate-700 bg-slate-900 py-2 shadow-xl"
            role="listbox"
          >
            <p v-if="searchLoading" class="px-3 py-2 text-xs text-slate-500">Searching…</p>
            <template v-else-if="!debouncedQuery">
              <p class="px-3 py-2 text-xs text-slate-500">Type to search your decks and card fronts.</p>
            </template>
            <template v-else-if="!searchDecks.length && !searchCards.length">
              <p class="px-3 py-2 text-xs text-slate-500">No results.</p>
            </template>
            <template v-else>
              <div v-if="searchDecks.length" class="px-2 pb-1">
                <p class="px-1 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Decks</p>
                <ul class="space-y-0.5">
                  <li v-for="d in searchDecks" :key="'d-' + d._id">
                    <button
                      type="button"
                      class="w-full rounded-md px-2 py-2 text-left text-sm text-slate-200 hover:bg-slate-800"
                      @mousedown.prevent="goDeck(d._id)"
                    >
                      <span class="font-medium text-emerald-300/90">{{ d.title }}</span>
                    </button>
                  </li>
                </ul>
              </div>
              <div v-if="searchCards.length" class="border-t border-slate-800 px-2 pt-1">
                <p class="px-1 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Cards</p>
                <ul class="space-y-0.5">
                  <li v-for="c in searchCards" :key="'c-' + c._id">
                    <button
                      type="button"
                      class="w-full rounded-md px-2 py-2 text-left text-sm hover:bg-slate-800"
                      @mousedown.prevent="goCard(c.deck_id, c._id)"
                    >
                      <span class="block font-medium text-slate-100">{{ c.front?.content ?? '—' }}</span>
                      <span class="mt-0.5 block truncate text-xs text-slate-500">{{ c.deck_title }}</span>
                    </button>
                  </li>
                </ul>
              </div>
            </template>
          </div>
        </div>
      </div>
    </header>
    <main class="mx-auto max-w-5xl px-4 py-8">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { BookOpen, LogOut, Search } from 'lucide-vue-next'
import { onClickOutside, watchDebounced } from '@vueuse/core'

const auth = useAuthStore()
const router = useRouter()
const { api } = useApi()

const searchRootRef = ref<HTMLElement | null>(null)
const searchQuery = ref('')
const debouncedQuery = ref('')
const panelOpen = ref(false)
const searchLoading = ref(false)
const searchDecks = ref<{ _id: string; title: string }[]>([])
const searchCards = ref<{ _id: string; deck_id: string; deck_title: string; front?: { content?: string } }[]>([])

watchDebounced(
  searchQuery,
  (v) => {
    debouncedQuery.value = (v || '').trim()
  },
  { debounce: 300 },
)

watch(debouncedQuery, async (q) => {
  if (!import.meta.client || !auth.token) {
    searchDecks.value = []
    searchCards.value = []
    return
  }
  if (!q) {
    searchDecks.value = []
    searchCards.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  try {
    const data = await api<{ decks: typeof searchDecks.value; cards: typeof searchCards.value }>(
      `/search?q=${encodeURIComponent(q)}`,
    )
    searchDecks.value = data.decks ?? []
    searchCards.value = data.cards ?? []
  } catch {
    searchDecks.value = []
    searchCards.value = []
  } finally {
    searchLoading.value = false
  }
})

onClickOutside(searchRootRef, () => {
  panelOpen.value = false
})

function onSearchFocus() {
  panelOpen.value = true
}

function closePanel() {
  panelOpen.value = false
}

function goDeck(deckId: string) {
  closePanel()
  searchQuery.value = ''
  debouncedQuery.value = ''
  searchDecks.value = []
  searchCards.value = []
  router.push(`/deck/${deckId}`)
}

function goCard(deckId: string, cardId: string) {
  closePanel()
  searchQuery.value = ''
  debouncedQuery.value = ''
  searchDecks.value = []
  searchCards.value = []
  router.push({ path: `/deck/${deckId}`, query: { card_id: cardId } })
}

function onLogout() {
  auth.logout()
  searchQuery.value = ''
  debouncedQuery.value = ''
  searchDecks.value = []
  searchCards.value = []
  panelOpen.value = false
  router.push('/login')
}
</script>
