<template>
  <div>
    <NuxtLink to="/deck" class="text-sm text-slate-400 hover:text-emerald-400">← Back to decks</NuxtLink>

    <h1 class="mt-4 text-2xl font-semibold text-white">TOEIC vocabulary from text</h1>
    <p class="mt-2 max-w-2xl text-sm text-slate-400">
      Paste reading or listening script text. AI suggests harder, TOEIC-style vocabulary (target
      <span class="text-slate-300">750+</span>), each with CEFR, a 1–10 difficulty score, POS, and Vietnamese gloss.
      Review, edit, then add to a deck (score and CEFR are copied into the card note).
    </p>

    <div class="mt-6 space-y-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <label class="block text-sm font-medium text-slate-300">Text</label>
      <textarea
        v-model="pasteText"
        rows="12"
        class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        placeholder="Paste English text here (max 35,000 characters)…"
      />
      <div class="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
        <span>{{ pasteText.length.toLocaleString() }} / 35,000 characters</span>
        <div class="flex items-center gap-2">
          <label for="max-terms" class="text-slate-400">Max terms</label>
          <input
            id="max-terms"
            v-model.number="maxTerms"
            type="number"
            min="1"
            max="100"
            class="w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-slate-200"
          />
        </div>
      </div>
      <button
        type="button"
        class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="analyzeDisabled"
        @click="runAnalyze"
      >
        {{ analyzeLoading ? 'Analyzing…' : 'Analyze text' }}
      </button>
      <p v-if="analyzeError" class="text-sm text-amber-300">{{ analyzeError }}</p>
      <p v-if="analyzeHint" class="text-xs text-slate-500">{{ analyzeHint }}</p>
    </div>

    <div v-if="warnings.length" class="mt-4 rounded-lg border border-amber-900/50 bg-amber-950/20 p-3 text-sm text-amber-200/90">
      <p class="font-medium text-amber-100">Warnings</p>
      <ul class="mt-1 list-inside list-disc text-amber-200/80">
        <li v-for="(w, i) in warnings" :key="i">{{ w }}</li>
      </ul>
    </div>

    <div v-if="terms.length" class="mt-8">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-lg font-semibold text-white">Results ({{ terms.length }})</h2>
        <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-400">
          <input type="checkbox" class="rounded border-slate-600" :checked="allSelected" @change="toggleSelectAll" />
          Select all
        </label>
      </div>

      <div class="mt-4 overflow-x-auto rounded-xl border border-slate-800">
        <table class="w-full min-w-[860px] text-left text-sm text-slate-200">
          <thead class="border-b border-slate-800 bg-slate-900/80 text-xs uppercase text-slate-500">
            <tr>
              <th class="w-10 px-3 py-2" />
              <th class="px-3 py-2">Word</th>
              <th class="w-14 px-2 py-2">Score</th>
              <th class="w-16 px-2 py-2">CEFR</th>
              <th class="px-3 py-2">POS</th>
              <th class="px-3 py-2">Meaning (VI)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in terms" :key="i" class="border-b border-slate-800/80">
              <td class="px-3 py-2 align-top">
                <input v-model="row.selected" type="checkbox" class="rounded border-slate-600" />
              </td>
              <td class="px-3 py-2 align-top">
                <input
                  v-model="row.word"
                  class="w-full min-w-[8rem] rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
                />
              </td>
              <td class="px-2 py-2 align-top text-center font-medium tabular-nums text-emerald-300/90">
                {{ row.difficulty_score ?? '—' }}
              </td>
              <td class="px-2 py-2 align-top text-center text-slate-400">{{ row.cefr ?? '—' }}</td>
              <td class="px-3 py-2 align-top text-slate-400">{{ row.part_of_speech }}</td>
              <td class="px-3 py-2 align-top">
                <input
                  v-model="row.meaning_vi"
                  class="w-full min-w-[12rem] rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-6 flex flex-col gap-4 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:flex-row sm:items-end">
        <div class="min-w-0 flex-1">
          <label class="block text-sm font-medium text-slate-300">Deck</label>
          <select
            v-model="selectedDeckId"
            class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
          >
            <option value="" disabled>Select a deck</option>
            <option v-for="d in decks" :key="d._id" :value="d._id">{{ d.title }} ({{ d.card_count ?? 0 }} cards)</option>
          </select>
        </div>
        <button
          type="button"
          class="rounded-lg border border-slate-600 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800"
          @click="openNewDeckModal"
        >
          New deck…
        </button>
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="addDisabled"
          @click="addToDeck"
        >
          {{ addLoading ? 'Adding…' : `Add ${selectedCount} card(s)` }}
        </button>
      </div>
      <p v-if="addMessage" class="mt-2 text-sm" :class="addOk ? 'text-emerald-400' : 'text-amber-300'">
        {{ addMessage }}
      </p>
    </div>

    <div
      v-if="newDeckOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-deck-title"
      @click.self="newDeckOpen = false"
    >
      <div class="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-xl">
        <h2 id="new-deck-title" class="text-lg font-semibold text-white">New deck</h2>
        <label class="mt-3 block text-sm text-slate-400">Title</label>
        <input
          v-model="newDeckTitle"
          type="text"
          class="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100"
          @keydown.enter.prevent="createDeckAndSelect"
        />
        <div class="mt-4 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-lg px-3 py-2 text-sm text-slate-400 hover:text-white"
            @click="newDeckOpen = false"
          >
            Cancel
          </button>
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
            :disabled="!newDeckTitle.trim() || newDeckLoading"
            @click="createDeckAndSelect"
          >
            {{ newDeckLoading ? 'Creating…' : 'Create' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

type TermRow = {
  word: string
  part_of_speech: string
  meaning_vi: string
  cefr?: string | null
  difficulty_score?: number | null
  note_en?: string | null
  selected: boolean
}

type DeckRow = { _id: string; title: string; card_count?: number }

const { api } = useApi()

const pasteText = ref('')
const maxTerms = ref(50)
const analyzeLoading = ref(false)
const analyzeError = ref('')
const analyzeHint = ref('')
const warnings = ref<string[]>([])
const terms = ref<TermRow[]>([])
const decks = ref<DeckRow[]>([])
const selectedDeckId = ref('')
const addLoading = ref(false)
const addMessage = ref('')
const addOk = ref(false)

const newDeckOpen = ref(false)
const newDeckTitle = ref('')
const newDeckLoading = ref(false)

const analyzeDisabled = computed(
  () =>
    analyzeLoading.value ||
    !pasteText.value.trim() ||
    pasteText.value.length > 35_000 ||
    maxTerms.value < 1 ||
    maxTerms.value > 100,
)

const selectedCount = computed(() => terms.value.filter((t) => t.selected).length)

const allSelected = computed(
  () => terms.value.length > 0 && terms.value.every((t) => t.selected),
)

const addDisabled = computed(
  () =>
    addLoading.value ||
    selectedCount.value === 0 ||
    !selectedDeckId.value,
)

async function loadDecks() {
  try {
    const data = await api<{ decks: DeckRow[] }>('/decks')
    decks.value = data.decks ?? []
  } catch {
    /* ignore */
  }
}

onMounted(() => {
  loadDecks()
})

function toggleSelectAll(e: Event) {
  const on = (e.target as HTMLInputElement).checked
  terms.value.forEach((t) => {
    t.selected = on
  })
}

async function runAnalyze() {
  analyzeError.value = ''
  analyzeHint.value = ''
  warnings.value = []
  terms.value = []
  analyzeLoading.value = true
  try {
    const data = await api<{
      terms: Array<{
        word: string
        part_of_speech: string
        meaning_vi: string
        cefr?: string | null
        difficulty_score?: number | null
        note_en?: string | null
      }>
      warnings?: string[]
    }>('/import/toeic-vocab', {
      method: 'POST',
      body: {
        text: pasteText.value,
        max_terms: maxTerms.value,
      },
    })
    warnings.value = data.warnings ?? []
    terms.value = (data.terms ?? []).map((t) => ({
      ...t,
      selected: true,
    }))
    if (!terms.value.length) {
      analyzeHint.value = 'No terms returned. Try shorter text or adjust max terms.'
    }
  } catch (e: unknown) {
    const err = e as { statusCode?: number; status?: number; data?: { detail?: unknown } }
    const code = err.statusCode ?? err.status
    const detail = err.data?.detail
    let msg = typeof detail === 'string' ? detail : 'Could not analyze text.'
    if (code === 429) msg += ' Rate limited — try again in a moment.'
    if (code === 503 || code === 502) msg += ' AI service unavailable — try again later.'
    if (code === 413) msg = 'Text is too long (max 35,000 characters).'
    analyzeError.value = msg
  } finally {
    analyzeLoading.value = false
  }
}

function openNewDeckModal() {
  newDeckTitle.value = ''
  newDeckOpen.value = true
}

async function createDeckAndSelect() {
  const title = newDeckTitle.value.trim()
  if (!title) return
  newDeckLoading.value = true
  try {
    const data = await api<{ deck: DeckRow }>('/decks', {
      method: 'POST',
      body: { title, description: '' },
    })
    const d = data.deck
    if (d?._id) {
      decks.value = [{ _id: d._id, title: d.title, card_count: d.card_count ?? 0 }, ...decks.value]
      selectedDeckId.value = d._id
      newDeckOpen.value = false
    }
  } catch {
    /* noop */
  } finally {
    newDeckLoading.value = false
  }
}

async function addToDeck() {
  addMessage.value = ''
  const deckId = selectedDeckId.value
  const rows = terms.value.filter((t) => t.selected && t.word.trim() && t.meaning_vi.trim())
  if (!deckId || !rows.length) return

  addLoading.value = true
  try {
    const cards = rows.map((t) => {
      const meta: string[] = []
      if (t.cefr?.trim()) meta.push(`CEFR: ${t.cefr.trim()}`)
      if (typeof t.difficulty_score === 'number' && !Number.isNaN(t.difficulty_score)) {
        meta.push(`TOEIC difficulty: ${t.difficulty_score}/10`)
      }
      const metaLine = meta.join(' · ')
      const noteParts = [t.note_en?.trim(), metaLine || null].filter(Boolean)
      const note = noteParts.length ? noteParts.join('\n') : undefined
      return {
        front: { content: t.word.trim() },
        back: { content: t.meaning_vi.trim() },
        card_type: 'vocab',
        part_of_speech: t.part_of_speech || undefined,
        ...(note ? { note } : {}),
      }
    })
    const data = await api<{ created: number; errors: Array<{ index: number; detail: string }> }>(
      `/decks/${deckId}/cards/batch`,
      {
        method: 'POST',
        body: { cards },
      },
    )
    const n = data.created ?? 0
    const errs = data.errors ?? []
    addOk.value = errs.length === 0
    addMessage.value =
      errs.length === 0
        ? `Added ${n} card(s) to the deck.`
        : `Added ${n} card(s). ${errs.length} row(s) failed.`
    await loadDecks()
    if (selectedDeckId.value) {
      const d = decks.value.find((x) => x._id === selectedDeckId.value)
      if (d && typeof d.card_count === 'number') {
        d.card_count = (d.card_count ?? 0) + n
      }
    }
  } catch (e: unknown) {
    addOk.value = false
    const err = e as { data?: { detail?: unknown } }
    const detail = err.data?.detail
    addMessage.value = typeof detail === 'string' ? detail : 'Could not add cards.'
  } finally {
    addLoading.value = false
  }
}
</script>
