<template>
  <div>
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <h2 class="text-2xl font-semibold text-white">Your decks</h2>
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        @click="showCreate = !showCreate"
      >
        <Plus class="h-4 w-4" />
        New deck
      </button>
    </div>

    <div
      v-if="showCreate"
      class="mt-6 rounded-xl border border-slate-800 bg-slate-900/50 p-4"
    >
      <Form :validation-schema="deckSchema" @submit="createDeck">
        <label class="mb-1 block text-sm font-medium text-slate-300">Title</label>
        <Field name="title" v-slot="{ field, errors }">
          <input
            v-bind="field"
            class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="e.g. Korean basics"
          />
          <p v-if="errors[0]" class="mt-1 text-sm text-red-400">{{ errors[0] }}</p>
        </Field>
        <div class="mt-3 flex gap-2">
          <button
            type="submit"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
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
      </Form>
    </div>

    <p v-if="loadError" class="mt-4 text-sm text-red-400">{{ loadError }}</p>

    <div
      v-if="decks.length"
      class="mt-8 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3"
    >
      <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-400">
        <input
          type="checkbox"
          class="rounded border-slate-600"
          :checked="allDecksSelected"
          @change="toggleSelectAllDecks"
        />
        Select all
      </label>
      <div v-if="selectedDeckIds.length" class="flex flex-wrap items-center gap-2">
        <span class="text-sm text-slate-400">{{ selectedDeckIds.length }} selected</span>
        <button
          type="button"
          class="rounded-lg bg-red-600/90 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-500"
          @click="openDeleteModal([...selectedDeckIds])"
        >
          Delete selected
        </button>
        <button
          type="button"
          class="text-sm text-slate-500 underline hover:text-slate-300"
          @click="clearDeckSelection"
        >
          Clear
        </button>
      </div>
    </div>

    <ul v-if="decks.length" class="mt-4 space-y-2">
      <li
        v-for="deck in decks"
        :key="deck._id"
        class="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-3 sm:px-4"
      >
        <input
          type="checkbox"
          class="shrink-0 rounded border-slate-600"
          :checked="selectedDeckIds.includes(deck._id)"
          @click.stop
          @change="toggleDeckSelection(deck._id)"
        />
        <div class="flex min-w-0 flex-1 flex-wrap items-center gap-3">
          <NuxtLink :to="`/deck/${deck._id}`" class="font-medium text-emerald-400 hover:underline">
            {{ deck.title }}
          </NuxtLink>
          <span class="text-sm text-slate-500">{{ deck.card_count ?? 0 }} cards</span>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <NuxtLink
            v-if="(deck.card_count ?? 0) > 0"
            :to="`/learning/session?deck_id=${deck._id}`"
            class="inline-flex items-center gap-1 rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
            @click.stop
          >
            <Play class="h-3.5 w-3.5" />
            Study
          </NuxtLink>
          <span
            v-else
            class="inline-flex cursor-not-allowed items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-500 opacity-70"
            title="Add cards to this deck before studying"
            aria-label="Study unavailable: add cards to this deck first"
            @click.stop
          >
            <Play class="h-3.5 w-3.5" />
            Study
          </span>
          <button
            type="button"
            class="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-red-400"
            aria-label="Delete deck"
            @click.stop="openDeleteModal([deck._id])"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </li>
    </ul>
    <p v-else-if="!pending" class="mt-8 text-center text-slate-500">No decks yet. Create one above.</p>
    <p v-if="pending" class="mt-8 text-center text-slate-500">Loading…</p>

    <ConfirmModal
      v-model="deleteModalOpen"
      :title="deleteModalTitle"
      :message="deleteModalMessage"
      confirm-label="Delete"
      @confirm="executeDeckDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { Form, Field } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/yup'
import * as yup from 'yup'
import { Plus, Play, Trash2 } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

type DeckRow = { _id: string; title: string; card_count?: number }

const { api } = useApi()
const decks = ref<DeckRow[]>([])
const showCreate = ref(false)
const pending = ref(true)
const loadError = ref('')
const selectedDeckIds = ref<string[]>([])
const deleteModalOpen = ref(false)
const pendingDeleteIds = ref<string[]>([])

const allDecksSelected = computed(
  () =>
    decks.value.length > 0 &&
    decks.value.every((d) => selectedDeckIds.value.includes(d._id)),
)

const deleteModalTitle = computed(() =>
  pendingDeleteIds.value.length > 1 ? 'Delete decks?' : 'Delete deck?',
)

const deleteModalMessage = computed(() => {
  const ids = pendingDeleteIds.value
  if (ids.length === 0) return ''
  if (ids.length === 1) {
    const d = decks.value.find((x) => x._id === ids[0])
    const name = d?.title ?? 'this deck'
    return `Delete “${name}” and all of its cards? This cannot be undone.`
  }
  return `Delete ${ids.length} decks and all cards inside them? This cannot be undone.`
})

const deckSchema = toTypedSchema(
  yup.object({
    title: yup.string().min(1, 'Title is required').required(),
  }),
)

function toggleDeckSelection(id: string) {
  const s = new Set(selectedDeckIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedDeckIds.value = [...s]
}

function toggleSelectAllDecks() {
  if (allDecksSelected.value) {
    selectedDeckIds.value = []
  } else {
    selectedDeckIds.value = decks.value.map((d) => d._id)
  }
}

function clearDeckSelection() {
  selectedDeckIds.value = []
}

function openDeleteModal(ids: string[]) {
  pendingDeleteIds.value = [...ids]
  deleteModalOpen.value = true
}

async function fetchDecks() {
  pending.value = true
  loadError.value = ''
  try {
    const data = await api<{ decks: DeckRow[] }>('/decks')
    decks.value = data.decks || []
    const idSet = new Set(decks.value.map((d) => d._id))
    selectedDeckIds.value = selectedDeckIds.value.filter((id) => idSet.has(id))
  } catch {
    loadError.value = 'Could not load decks'
    decks.value = []
  } finally {
    pending.value = false
  }
}

onMounted(fetchDecks)

async function createDeck(values: { title: string }) {
  try {
    await api('/decks', { method: 'POST', body: { title: values.title } })
    showCreate.value = false
    await fetchDecks()
  } catch {
    loadError.value = 'Could not create deck'
  }
}

async function executeDeckDelete() {
  const ids = pendingDeleteIds.value
  pendingDeleteIds.value = []
  let failed = false
  for (const id of ids) {
    try {
      await api(`/decks/${id}`, { method: 'DELETE' })
    } catch {
      failed = true
    }
  }
  if (failed) {
    loadError.value = 'Could not delete one or more decks'
  } else {
    loadError.value = ''
  }
  selectedDeckIds.value = selectedDeckIds.value.filter((id) => !ids.includes(id))
  await fetchDecks()
}
</script>
