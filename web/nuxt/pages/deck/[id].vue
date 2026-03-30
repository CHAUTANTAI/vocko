<template>
  <div>
    <NuxtLink to="/deck" class="text-sm text-slate-400 hover:text-emerald-400">← Back to decks</NuxtLink>

    <div v-if="deck" class="mt-4">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 class="text-2xl font-semibold text-white">{{ deck.title }}</h2>
          <p v-if="deck.description" class="mt-1 text-slate-400">{{ deck.description }}</p>
        </div>
        <NuxtLink
          :to="`/learning/session?deck_id=${route.params.id}`"
          class="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        >
          <Play class="h-4 w-4" />
          Study deck
        </NuxtLink>
      </div>

      <div class="mt-6">
        <label class="mb-2 block text-sm font-medium text-slate-300">Search cards</label>
        <div class="relative max-w-md">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            v-model="searchQuery"
            type="search"
            class="w-full rounded-lg border border-slate-700 bg-slate-900 py-2 pl-10 pr-3 text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="Filter by front or back…"
          />
        </div>
      </div>

      <div
        class="mt-6 rounded-xl border border-slate-800 bg-slate-900/50 p-4"
      >
        <button
          type="button"
          class="text-sm font-medium text-emerald-400 hover:underline"
          @click="showAdd = !showAdd"
        >
          {{ showAdd ? 'Close form' : '+ Add card' }}
        </button>
        <Form v-if="showAdd" class="mt-4 space-y-3" :validation-schema="cardSchema" @submit="addCard">
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-400">Front</label>
            <Field name="front" v-slot="{ field, errors }">
              <input
                v-bind="field"
                class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
              />
              <p v-if="errors[0]" class="mt-1 text-xs text-red-400">{{ errors[0] }}</p>
            </Field>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-400">Back</label>
            <Field name="back" v-slot="{ field, errors }">
              <input
                v-bind="field"
                class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
              />
              <p v-if="errors[0]" class="mt-1 text-xs text-red-400">{{ errors[0] }}</p>
            </Field>
          </div>
          <div>
            <label class="mb-1 block text-xs font-medium text-slate-400">Hint (optional)</label>
            <Field name="hint" v-slot="{ field }">
              <input
                v-bind="field"
                class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
                placeholder="Shown during study if set"
              />
            </Field>
          </div>
          <button
            type="submit"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
          >
            Add card
          </button>
        </Form>
      </div>

      <ul class="mt-6 space-y-2">
        <li
          v-for="card in displayedCards"
          :key="card._id"
          class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/30 px-4 py-3 text-sm"
        >
          <span class="text-slate-200">
            <span class="font-medium text-slate-100">{{ card.front?.content ?? '—' }}</span>
            <span class="mx-2 text-slate-600">→</span>
            <span class="text-slate-400">{{ card.back?.content ?? '—' }}</span>
          </span>
          <button
            type="button"
            class="rounded-md p-1.5 text-slate-500 hover:bg-slate-800 hover:text-red-400"
            aria-label="Delete card"
            @click="remove(card._id)"
          >
            <Trash2 class="h-4 w-4" />
          </button>
        </li>
      </ul>
      <p v-if="!displayedCards.length && cards.length" class="mt-4 text-center text-slate-500">
        No cards match your search.
      </p>
      <p v-if="!cards.length && !pending" class="mt-4 text-center text-slate-500">No cards in this deck yet.</p>
    </div>
    <p v-else-if="pending" class="mt-8 text-slate-500">Loading…</p>
    <p v-else class="mt-8 text-red-400">Deck not found.</p>
  </div>
</template>

<script setup lang="ts">
import Fuse from 'fuse.js'
import { Form, Field } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/yup'
import * as yup from 'yup'
import { Play, Search, Trash2 } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

const route = useRoute()
const { api } = useApi()

const deck = ref<Record<string, unknown> | null>(null)
const cards = ref<
  {
    _id: string
    front?: { content?: string }
    back?: { content?: string }
    hint?: string
    tags?: string[]
  }[]
>([])
const showAdd = ref(false)
const pending = ref(true)
const searchQuery = ref('')

const cardSchema = toTypedSchema(
  yup.object({
    front: yup.string().min(1, 'Front is required').required(),
    back: yup.string().min(1, 'Back is required').required(),
    hint: yup.string().optional(),
  }),
)

const fuse = computed(() =>
  new Fuse(cards.value, {
    keys: [
      { name: 'front.content', weight: 0.5 },
      { name: 'back.content', weight: 0.5 },
      'tags',
    ],
    threshold: 0.4,
  }),
)

const displayedCards = computed(() => {
  const q = searchQuery.value.trim()
  if (!q) return cards.value
  return fuse.value.search(q).map((r) => r.item)
})

async function fetchDeck() {
  pending.value = true
  try {
    const data = await api<{ deck: Record<string, unknown>; cards?: typeof cards.value }>(
      `/decks/${route.params.id}?include_cards=true`,
    )
    deck.value = data.deck
    cards.value = data.cards || []
  } catch {
    deck.value = null
    cards.value = []
  } finally {
    pending.value = false
  }
}

onMounted(fetchDeck)
watch(() => route.params.id, fetchDeck)

async function addCard(values: { front: string; back: string; hint?: string }) {
  const body: Record<string, unknown> = {
    front: { content: values.front },
    back: { content: values.back },
  }
  const h = values.hint?.trim()
  if (h) body.hint = h
  await api(`/decks/${route.params.id}/cards`, {
    method: 'POST',
    body,
  })
  showAdd.value = false
  await fetchDeck()
}

async function remove(id: string) {
  await api(`/cards/${id}`, { method: 'DELETE' })
  await fetchDeck()
}
</script>
