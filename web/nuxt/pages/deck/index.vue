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

    <ul v-if="decks.length" class="mt-8 space-y-2">
      <li
        v-for="deck in decks"
        :key="deck._id"
        class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
      >
        <div class="flex flex-wrap items-center gap-3">
          <NuxtLink :to="`/deck/${deck._id}`" class="font-medium text-emerald-400 hover:underline">
            {{ deck.title }}
          </NuxtLink>
          <span class="text-sm text-slate-500">{{ deck.card_count ?? 0 }} cards</span>
        </div>
        <div class="flex items-center gap-2">
          <NuxtLink
            :to="`/learning/session?deck_id=${deck._id}`"
            class="inline-flex items-center gap-1 rounded-md border border-slate-600 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
          >
            <Play class="h-3.5 w-3.5" />
            Study
          </NuxtLink>
          <button
            type="button"
            class="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-red-400"
            aria-label="Delete deck"
            @click="remove(deck._id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </div>
      </li>
    </ul>
    <p v-else-if="!pending" class="mt-8 text-center text-slate-500">No decks yet. Create one above.</p>
    <p v-if="pending" class="mt-8 text-center text-slate-500">Loading…</p>
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

const deckSchema = toTypedSchema(
  yup.object({
    title: yup.string().min(1, 'Title is required').required(),
  }),
)

async function fetchDecks() {
  pending.value = true
  loadError.value = ''
  try {
    const data = await api<{ decks: DeckRow[] }>('/decks')
    decks.value = data.decks || []
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

async function remove(id: string) {
  if (!confirm('Delete this deck and all its cards?')) return
  try {
    await api(`/decks/${id}`, { method: 'DELETE' })
    await fetchDecks()
  } catch {
    loadError.value = 'Could not delete deck'
  }
}
</script>
