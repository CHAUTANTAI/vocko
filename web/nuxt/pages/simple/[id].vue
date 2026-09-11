<template>
  <div>
    <div class="flex flex-wrap items-center gap-3">
      <NuxtLink to="/simple" class="text-sm text-slate-400 hover:text-emerald-400">← Simple decks</NuxtLink>
    </div>

    <div v-if="deck" class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-white">{{ deck.title }}</h2>
        <p v-if="deck.description" class="mt-1 text-sm text-slate-400">{{ deck.description }}</p>
        <p class="mt-1 text-sm text-slate-500">
          {{ draftCards.length }} cards
          <span v-if="isDirty" class="ml-2 text-amber-300/90">· unsaved changes</span>
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-40"
          :disabled="!isDirty || saving"
          @click="discardChanges"
        >
          Discard
        </button>
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40"
          :disabled="!isDirty || saving"
          @click="saveAll"
        >
          {{ saving ? 'Saving…' : 'Save' }}
        </button>
        <NuxtLink
          v-if="savedCards.length && !isDirty"
          :to="`/simple/study?deck_id=${deck._id}`"
          class="inline-flex items-center gap-2 rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
        >
          <Play class="h-4 w-4" />
          Study
        </NuxtLink>
        <span
          v-else-if="draftCards.length"
          class="inline-flex cursor-not-allowed items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-500"
          :title="isDirty ? 'Save changes before studying' : 'Add cards first'"
        >
          <Play class="h-4 w-4" />
          Study
        </span>
      </div>
    </div>

    <p v-if="error" class="mt-4 text-sm text-red-400">{{ error }}</p>
    <p v-if="saveOk" class="mt-4 text-sm text-emerald-400">Saved.</p>

    <div class="mt-6 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <h3 class="text-sm font-medium text-slate-200">Add card</h3>
      <p class="mt-1 text-xs text-slate-500">
        Bold / italic / lists supported. Adds to the local draft — click Save to persist.
      </p>
      <div class="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <label class="mb-1 block text-xs text-slate-400">Front</label>
          <RichTextEditor v-model="newFront" />
        </div>
        <div>
          <label class="mb-1 block text-xs text-slate-400">Back</label>
          <RichTextEditor v-model="newBack" />
        </div>
      </div>
      <button
        type="button"
        class="mt-3 rounded-lg border border-emerald-800/70 bg-emerald-950/30 px-3 py-1.5 text-sm font-medium text-emerald-200 hover:bg-emerald-950/50"
        @click="addDraftCard"
      >
        Add to draft
      </button>
    </div>

    <div class="mt-6">
      <input
        v-model="searchQ"
        type="search"
        placeholder="Filter front or back (local)…"
        class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
      />
    </div>

    <ul class="mt-4 space-y-2">
      <li
        v-for="card in filteredDraftCards"
        :key="card._id"
        class="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-3"
        :class="{
          'border-emerald-900/50': card._id.startsWith('tmp_'),
          'opacity-60 line-through': deletedIds.has(card._id),
        }"
      >
        <div v-if="editingId === card._id" class="grid gap-2 sm:grid-cols-2">
          <div>
            <label class="mb-1 block text-xs text-slate-400">Front</label>
            <RichTextEditor v-model="editFront" />
          </div>
          <div>
            <label class="mb-1 block text-xs text-slate-400">Back</label>
            <RichTextEditor v-model="editBack" />
          </div>
          <div class="flex gap-2 sm:col-span-2">
            <button
              type="button"
              class="rounded-md bg-emerald-600 px-3 py-1 text-xs text-white"
              @click="applyEdit(card._id)"
            >
              Apply
            </button>
            <button
              type="button"
              class="rounded-md border border-slate-600 px-3 py-1 text-xs text-slate-300"
              @click="editingId = null"
            >
              Cancel
            </button>
          </div>
        </div>
        <div v-else class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0 flex-1 space-y-1">
            <div
              class="prose prose-invert prose-sm max-w-none font-medium text-slate-100"
              v-html="previewHtml(card.front)"
            />
            <div
              class="prose prose-invert prose-sm max-w-none text-slate-400"
              v-html="previewHtml(card.back)"
            />
            <p v-if="card._id.startsWith('tmp_')" class="text-[10px] uppercase tracking-wide text-emerald-500/80">
              New (draft)
            </p>
          </div>
          <div class="flex gap-2">
            <button
              type="button"
              class="text-xs text-slate-400 hover:text-emerald-400"
              :disabled="deletedIds.has(card._id)"
              @click="startEdit(card)"
            >
              Edit
            </button>
            <button
              v-if="!deletedIds.has(card._id)"
              type="button"
              class="text-xs text-red-300 hover:text-red-200"
              @click="markDelete(card._id)"
            >
              Delete
            </button>
            <button
              v-else
              type="button"
              class="text-xs text-slate-400 hover:text-emerald-400"
              @click="undelete(card._id)"
            >
              Undo delete
            </button>
          </div>
        </div>
      </li>
    </ul>
    <p v-if="!filteredDraftCards.length && !error" class="mt-4 text-sm text-slate-500">
      No cards{{ searchQ ? ' match' : ' yet' }}.
    </p>

    <div v-if="stats" class="mt-8 rounded-xl border border-slate-800 bg-slate-900/30 p-4">
      <h3 class="text-sm font-medium text-slate-200">Study stats</h3>
      <p class="mt-1 text-xs text-slate-500">
        Forgot {{ stats.forget_total }} · Remembered {{ stats.remember_total }}
      </p>
      <ul v-if="stats.hard_cards?.length" class="mt-3 space-y-1">
        <li v-for="h in stats.hard_cards" :key="h.card_id" class="text-xs text-slate-400">
          <span class="text-amber-300/90">{{ h.forget_count }}× forgot</span>
          — {{ plainPreview(h.front) }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Play } from 'lucide-vue-next'
import { useEventListener } from '@vueuse/core'
import { onBeforeRouteLeave } from 'vue-router'
import { htmlToPlainText, isEmptyRichText } from '~/utils/richText'
import { sanitizeRichHtml } from '~/utils/sanitizeRichHtml'

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
const savedCards = ref<SimpleCard[]>([])
const draftCards = ref<SimpleCard[]>([])
const deletedIds = ref<Set<string>>(new Set())
const error = ref('')
const saveOk = ref(false)
const saving = ref(false)
const newFront = ref('')
const newBack = ref('')
const searchQ = ref('')
const editingId = ref<string | null>(null)
const editFront = ref('')
const editBack = ref('')
let tmpSeq = 0

const stats = ref<{
  forget_total: number
  remember_total: number
  hard_cards: { card_id: string; front: string; forget_count: number }[]
} | null>(null)

function plainPreview(html: string) {
  return htmlToPlainText(html) || '—'
}

function previewHtml(raw: string) {
  const clean = sanitizeRichHtml(raw)
  if (clean.includes('<')) return clean
  const plain = htmlToPlainText(raw)
  if (!plain) return '<p></p>'
  return `<p>${plain
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')}</p>`
}

function normalizeSide(html: string) {
  return sanitizeRichHtml(html).trim()
}

const filteredDraftCards = computed(() => {
  const q = searchQ.value.trim().toLowerCase()
  const list = draftCards.value
  if (!q) return list
  return list.filter(
    (c) =>
      htmlToPlainText(c.front).toLowerCase().includes(q) ||
      htmlToPlainText(c.back).toLowerCase().includes(q),
  )
})

const isDirty = computed(() => {
  if (deletedIds.value.size > 0) return true
  if (draftCards.value.some((c) => c._id.startsWith('tmp_'))) return true
  const savedMap = new Map(savedCards.value.map((c) => [c._id, c]))
  for (const c of draftCards.value) {
    if (c._id.startsWith('tmp_')) continue
    if (deletedIds.value.has(c._id)) continue
    const s = savedMap.get(c._id)
    if (!s || s.front !== c.front || s.back !== c.back) return true
  }
  return false
})

function cloneCards(list: SimpleCard[]) {
  return list.map((c) => ({ ...c }))
}

function resetDraftFromSaved() {
  draftCards.value = cloneCards(savedCards.value)
  deletedIds.value = new Set()
  editingId.value = null
}

async function loadDeck() {
  error.value = ''
  saveOk.value = false
  try {
    const data = await api<SimpleDeck>(`/simple/decks/${deckId.value}`)
    deck.value = data
    savedCards.value = data.cards ?? []
    resetDraftFromSaved()
  } catch {
    error.value = 'Failed to load deck'
    deck.value = null
    savedCards.value = []
    draftCards.value = []
  }
}

async function loadStats() {
  try {
    stats.value = await api(`/simple/decks/${deckId.value}/stats`)
  } catch {
    stats.value = null
  }
}

function addDraftCard() {
  const front = normalizeSide(newFront.value)
  const back = normalizeSide(newBack.value)
  if (isEmptyRichText(front) || isEmptyRichText(back)) return
  tmpSeq += 1
  draftCards.value.push({
    _id: `tmp_${Date.now()}_${tmpSeq}`,
    deck_id: deckId.value,
    front,
    back,
  })
  newFront.value = ''
  newBack.value = ''
  saveOk.value = false
}

function startEdit(card: SimpleCard) {
  editingId.value = card._id
  editFront.value = card.front
  editBack.value = card.back
}

function applyEdit(id: string) {
  const front = normalizeSide(editFront.value)
  const back = normalizeSide(editBack.value)
  if (isEmptyRichText(front) || isEmptyRichText(back)) return
  const idx = draftCards.value.findIndex((c) => c._id === id)
  if (idx < 0) return
  draftCards.value[idx] = { ...draftCards.value[idx], front, back }
  editingId.value = null
  saveOk.value = false
}

function markDelete(id: string) {
  if (id.startsWith('tmp_')) {
    draftCards.value = draftCards.value.filter((c) => c._id !== id)
    if (editingId.value === id) editingId.value = null
    return
  }
  const next = new Set(deletedIds.value)
  next.add(id)
  deletedIds.value = next
  if (editingId.value === id) editingId.value = null
  saveOk.value = false
}

function undelete(id: string) {
  const next = new Set(deletedIds.value)
  next.delete(id)
  deletedIds.value = next
  saveOk.value = false
}

function discardChanges() {
  resetDraftFromSaved()
  saveOk.value = false
  error.value = ''
}

function buildSyncPayload() {
  const create = draftCards.value
    .filter((c) => c._id.startsWith('tmp_'))
    .map((c) => ({ front: normalizeSide(c.front), back: normalizeSide(c.back) }))

  const savedMap = new Map(savedCards.value.map((c) => [c._id, c]))
  const update = draftCards.value
    .filter((c) => !c._id.startsWith('tmp_') && !deletedIds.value.has(c._id))
    .filter((c) => {
      const s = savedMap.get(c._id)
      return !s || s.front !== c.front || s.back !== c.back
    })
    .map((c) => ({
      id: c._id,
      front: normalizeSide(c.front),
      back: normalizeSide(c.back),
    }))

  const delete_ids = [...deletedIds.value]
  return { create, update, delete_ids }
}

async function saveAll() {
  if (!isDirty.value || saving.value) return
  error.value = ''
  saveOk.value = false
  saving.value = true
  try {
    const body = buildSyncPayload()
    const data = await api<{
      deck: SimpleDeck
      cards: SimpleCard[]
    }>(`/simple/decks/${deckId.value}/cards/sync`, {
      method: 'POST',
      body,
    })
    deck.value = data.deck
    savedCards.value = data.cards ?? []
    resetDraftFromSaved()
    saveOk.value = true
    await loadStats()
  } catch {
    error.value = 'Failed to save changes'
  } finally {
    saving.value = false
  }
}

onBeforeRouteLeave(() => {
  if (!isDirty.value) return true
  return window.confirm('You have unsaved changes. Leave without saving?')
})

if (import.meta.client) {
  useEventListener(window, 'beforeunload', (e) => {
    if (!isDirty.value) return
    e.preventDefault()
    e.returnValue = ''
  })
}

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
