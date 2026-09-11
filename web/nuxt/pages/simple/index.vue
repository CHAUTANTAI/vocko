<template>
  <div>
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <h2 class="text-2xl font-semibold text-white">Simple flashcards</h2>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        @click="showCreate = !showCreate"
      >
        <Plus class="h-4 w-4" />
        New deck
      </button>
    </div>
    <p class="mt-2 text-sm text-slate-400">
      Plain front/back cards with basic formatting. Study with Remembered / Forgot — forgotten cards return to the end of the queue.
    </p>

    <div
      v-if="showCreate"
      class="mt-6 rounded-xl border border-slate-800 bg-slate-900/50 p-4"
    >
      <label class="mb-1 block text-sm font-medium text-slate-300">Title</label>
      <input
        v-model="newTitle"
        class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        placeholder="e.g. Kitchen vocabulary"
        @keydown.enter.prevent="createDeck"
      />
      <label class="mb-1 mt-3 block text-sm font-medium text-slate-300">Description (optional)</label>
      <input
        v-model="newDescription"
        class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
      />
      <div class="mt-3 flex gap-2">
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
          @click="createDeck"
        >
          Create
        </button>
        <button
          type="button"
          class="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-800"
          @click="showCreate = false"
        >
          Cancel
        </button>
      </div>
    </div>

    <p v-if="loadError" class="mt-4 text-sm text-red-400">{{ loadError }}</p>

    <ul v-if="decks.length" class="mt-8 space-y-2">
      <li
        v-for="deck in decks"
        :key="deck._id"
        class="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-3 sm:px-4"
      >
        <div class="flex min-w-0 flex-1 flex-wrap items-center gap-3">
          <NuxtLink
            :to="`/simple/${deck._id}`"
            class="font-medium text-emerald-400 hover:underline"
          >
            {{ deck.title }}
          </NuxtLink>
          <span class="text-sm text-slate-500">{{ deck.card_count ?? 0 }} cards</span>
        </div>
        <div class="flex shrink-0 flex-wrap items-center gap-2">
          <NuxtLink
            v-if="(deck.card_count ?? 0) > 0"
            :to="`/simple/study?deck_id=${deck._id}`"
            class="inline-flex items-center gap-1 rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
          >
            <Play class="h-3.5 w-3.5" />
            Study
          </NuxtLink>
          <button
            type="button"
            class="rounded-md border border-red-900/60 px-2 py-1 text-xs text-red-300 hover:bg-red-950/40"
            @click="confirmDelete(deck)"
          >
            Delete
          </button>
        </div>
      </li>
    </ul>
    <p v-else-if="!loadError" class="mt-8 text-sm text-slate-500">No simple decks yet.</p>

    <ConfirmModal
      v-model="deleteModalOpen"
      title="Delete simple deck?"
      :message="pendingDelete ? `Delete “${pendingDelete.title}” and all its cards?` : ''"
      confirm-label="Delete"
      @cancel="pendingDelete = null"
      @confirm="doDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { Play, Plus } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

type SimpleDeck = {
  _id: string
  title: string
  description?: string
  card_count?: number
}

const { api } = useApi()
const decks = ref<SimpleDeck[]>([])
const loadError = ref('')
const showCreate = ref(false)
const newTitle = ref('')
const newDescription = ref('')
const pendingDelete = ref<SimpleDeck | null>(null)
const deleteModalOpen = ref(false)

async function load() {
  loadError.value = ''
  try {
    const data = await api<{ decks: SimpleDeck[] }>('/simple/decks')
    decks.value = data.decks ?? []
  } catch {
    loadError.value = 'Failed to load simple decks'
  }
}

async function createDeck() {
  const title = newTitle.value.trim()
  if (!title) return
  try {
    await api('/simple/decks', {
      method: 'POST',
      body: { title, description: newDescription.value.trim() },
    })
    newTitle.value = ''
    newDescription.value = ''
    showCreate.value = false
    await load()
  } catch {
    loadError.value = 'Failed to create deck'
  }
}

function confirmDelete(deck: SimpleDeck) {
  pendingDelete.value = deck
  deleteModalOpen.value = true
}

async function doDelete() {
  const d = pendingDelete.value
  pendingDelete.value = null
  deleteModalOpen.value = false
  if (!d) return
  try {
    await api(`/simple/decks/${d._id}`, { method: 'DELETE' })
    await load()
  } catch {
    loadError.value = 'Failed to delete deck'
  }
}

onMounted(load)
</script>
