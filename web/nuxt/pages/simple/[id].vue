<template>
  <div>
    <div class="flex flex-wrap items-center gap-3">
      <NuxtLink to="/simple" class="text-sm text-slate-400 hover:text-emerald-400">← Simple decks</NuxtLink>
    </div>

    <div v-if="deck" class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-white">{{ deck.title }}</h2>
        <p v-if="deck.description" class="mt-1 text-sm text-slate-400">{{ deck.description }}</p>
        <p class="mt-1 text-sm text-slate-500">{{ cards.length }} cards</p>
      </div>
      <NuxtLink
        v-if="cards.length"
        :to="`/simple/study?deck_id=${deck._id}`"
        class="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
      >
        <Play class="h-4 w-4" />
        Study
      </NuxtLink>
    </div>

    <p v-if="error" class="mt-4 text-sm text-red-400">{{ error }}</p>

    <div class="mt-6 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <h3 class="text-sm font-medium text-slate-200">Add card</h3>
      <div class="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-xs text-slate-400">Front</label>
          <textarea
            v-model="newFront"
            rows="2"
            class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs text-slate-400">Back</label>
          <textarea
            v-model="newBack"
            rows="2"
            class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      </div>
      <button
        type="button"
        class="mt-3 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500"
        @click="addCard"
      >
        Add
      </button>
    </div>

    <div class="mt-6">
      <input
        v-model="searchQ"
        type="search"
        placeholder="Search front or back…"
        class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
      />
    </div>

    <ul class="mt-4 space-y-2">
      <li
        v-for="card in cards"
        :key="card._id"
        class="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-3"
      >
        <div v-if="editingId === card._id" class="grid gap-2 sm:grid-cols-2">
          <textarea v-model="editFront" rows="2" class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
          <textarea v-model="editBack" rows="2" class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
          <div class="flex gap-2 sm:col-span-2">
            <button type="button" class="rounded-md bg-emerald-600 px-3 py-1 text-xs text-white" @click="saveEdit(card._id)">Save</button>
            <button type="button" class="rounded-md border border-slate-600 px-3 py-1 text-xs text-slate-300" @click="editingId = null">Cancel</button>
          </div>
        </div>
        <div v-else class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium text-slate-100">{{ card.front }}</p>
            <p class="mt-1 text-sm text-slate-400">{{ card.back }}</p>
          </div>
          <div class="flex gap-2">
            <button type="button" class="text-xs text-slate-400 hover:text-emerald-400" @click="startEdit(card)">Edit</button>
            <button type="button" class="text-xs text-red-300 hover:text-red-200" @click="removeCard(card._id)">Delete</button>
          </div>
        </div>
      </li>
    </ul>
    <p v-if="!cards.length && !error" class="mt-4 text-sm text-slate-500">No cards{{ searchQ ? ' match' : ' yet' }}.</p>

    <div v-if="stats" class="mt-8 rounded-xl border border-slate-800 bg-slate-900/30 p-4">
      <h3 class="text-sm font-medium text-slate-200">Study stats</h3>
      <p class="mt-1 text-xs text-slate-500">
        Forgot {{ stats.forget_total }} · Remembered {{ stats.remember_total }}
      </p>
      <ul v-if="stats.hard_cards?.length" class="mt-3 space-y-1">
        <li v-for="h in stats.hard_cards" :key="h.card_id" class="text-xs text-slate-400">
          <span class="text-amber-300/90">{{ h.forget_count }}× forgot</span>
          — {{ h.front }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Play } from 'lucide-vue-next'
import { watchDebounced } from '@vueuse/core'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

type SimpleCard = { _id: string; front: string; back: string; deck_id: string }
type SimpleDeck = {
  _id: string
  title: string
  description?: string
  card_count?: number
  cards?: SimpleCard[]
}

const route = useRoute()
const { api } = useApi()
const deckId = computed(() => String(route.params.id || ''))

const deck = ref<SimpleDeck | null>(null)
const cards = ref<SimpleCard[]>([])
const error = ref('')
const newFront = ref('')
const newBack = ref('')
const searchQ = ref('')
const editingId = ref<string | null>(null)
const editFront = ref('')
const editBack = ref('')
const stats = ref<{
  forget_total: number
  remember_total: number
  hard_cards: { card_id: string; front: string; forget_count: number }[]
} | null>(null)

async function loadDeck() {
  error.value = ''
  try {
    const data = await api<SimpleDeck>(`/simple/decks/${deckId.value}`)
    deck.value = data
    cards.value = data.cards ?? []
  } catch {
    error.value = 'Failed to load deck'
    deck.value = null
    cards.value = []
  }
}

async function loadCards() {
  if (!deckId.value) return
  try {
    const q = searchQ.value.trim()
    const data = await api<{ cards: SimpleCard[] }>(
      `/simple/decks/${deckId.value}/cards${q ? `?q=${encodeURIComponent(q)}` : ''}`,
    )
    cards.value = data.cards ?? []
  } catch {
    error.value = 'Failed to search cards'
  }
}

async function loadStats() {
  try {
    stats.value = await api(`/simple/decks/${deckId.value}/stats`)
  } catch {
    stats.value = null
  }
}

async function addCard() {
  const front = newFront.value.trim()
  const back = newBack.value.trim()
  if (!front || !back) return
  try {
    await api(`/simple/decks/${deckId.value}/cards`, {
      method: 'POST',
      body: { front, back },
    })
    newFront.value = ''
    newBack.value = ''
    searchQ.value = ''
    await loadDeck()
    await loadStats()
  } catch {
    error.value = 'Failed to add card'
  }
}

function startEdit(card: SimpleCard) {
  editingId.value = card._id
  editFront.value = card.front
  editBack.value = card.back
}

async function saveEdit(id: string) {
  const front = editFront.value.trim()
  const back = editBack.value.trim()
  if (!front || !back) return
  try {
    await api(`/simple/cards/${id}`, { method: 'PATCH', body: { front, back } })
    editingId.value = null
    await loadCards()
  } catch {
    error.value = 'Failed to update card'
  }
}

async function removeCard(id: string) {
  try {
    await api(`/simple/cards/${id}`, { method: 'DELETE' })
    await loadDeck()
    if (searchQ.value.trim()) await loadCards()
    await loadStats()
  } catch {
    error.value = 'Failed to delete card'
  }
}

watchDebounced(searchQ, () => loadCards(), { debounce: 250 })

watch(
  deckId,
  async (id) => {
    if (!id) return
    await loadDeck()
    await loadStats()
  },
  { immediate: true },
)
</script>
