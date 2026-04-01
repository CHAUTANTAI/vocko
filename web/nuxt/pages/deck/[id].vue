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
          v-if="canStudy"
          :to="`/learning/session?deck_id=${route.params.id}`"
          class="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        >
          <Play class="h-4 w-4" />
          Study deck
        </NuxtLink>
        <div
          v-else
          class="inline-flex flex-col items-stretch gap-1 sm:items-end"
        >
          <span
            class="inline-flex cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900/50 px-4 py-2 text-sm font-medium text-slate-500"
            title="Add at least one card before studying"
            aria-label="Study unavailable: add at least one card first"
          >
            <Play class="h-4 w-4" />
            Study deck
          </span>
          <span class="text-xs text-slate-500">Add at least one card to start a session.</span>
        </div>
      </div>

      <div
        v-if="deckStats || weakTags.length"
        class="mt-6 grid gap-4 lg:grid-cols-2"
      >
        <div
          v-if="deckStats"
          class="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300"
        >
          <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Study snapshot</h3>
          <dl class="mt-3 space-y-2">
            <div class="flex justify-between gap-2">
              <dt class="text-slate-500">Answers in this deck</dt>
              <dd class="font-medium text-slate-200">{{ deckStats.study_records_total }}</dd>
            </div>
            <div v-if="deckStats.study_records_total > 0" class="flex justify-between gap-2">
              <dt class="text-slate-500">Accuracy</dt>
              <dd class="font-medium text-slate-200">
                {{ Math.round((deckStats.accuracy ?? 0) * 100) }}%
              </dd>
            </div>
            <div class="flex justify-between gap-2">
              <dt class="text-slate-500">Best streak (any card)</dt>
              <dd class="font-medium text-slate-200">{{ deckStats.streak_max }}</dd>
            </div>
          </dl>
          <p v-if="deckStats.study_records_total === 0" class="mt-2 text-xs text-slate-500">
            Study a session to see accuracy; tags on cards improve weak-topic ranking after wrong answers.
          </p>
        </div>
        <div
          v-if="weakTags.length"
          class="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-300"
        >
          <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500">Weak tags (incorrect)</h3>
          <ul class="mt-3 space-y-1.5">
            <li
              v-for="t in weakTags.slice(0, 8)"
              :key="t.tag_id"
              class="flex justify-between gap-2 text-slate-200"
            >
              <span>{{ t.name }}</span>
              <span class="shrink-0 text-slate-500">{{ t.incorrect_count }}×</span>
            </li>
          </ul>
        </div>
        <p
          v-else-if="deckStats && deckStats.study_records_total > 0"
          class="rounded-xl border border-dashed border-slate-800 bg-slate-900/20 p-4 text-xs text-slate-500 lg:col-span-2"
        >
          No tag-level mistakes yet. Add tags to cards and miss a few answers to see weak tags here; smart
          learn uses them to prioritize reviews.
        </p>
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
        v-if="cards.length"
        class="mt-6 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3"
      >
        <label class="flex cursor-pointer items-center gap-2 text-sm text-slate-400">
          <input
            type="checkbox"
            class="rounded border-slate-600"
            :checked="allDisplayedCardsSelected"
            @change="toggleSelectAllDisplayed"
          />
          Select visible{{ searchQuery.trim() ? ' (filtered)' : '' }}
        </label>
        <div v-if="selectedCardIds.length" class="flex flex-wrap items-center gap-2">
          <span class="text-sm text-slate-400">{{ selectedCardIds.length }} selected</span>
          <button
            type="button"
            class="rounded-lg bg-red-600/90 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-500"
            @click="openDeleteCardsModal([...selectedCardIds])"
          >
            Delete selected
          </button>
          <button
            type="button"
            class="text-sm text-slate-500 underline hover:text-slate-300"
            @click="clearCardSelection"
          >
            Clear
          </button>
        </div>
      </div>

      <div class="mt-6 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
        <button
          type="button"
          class="text-sm font-medium text-emerald-400 hover:underline"
          @click="toggleAddForm"
        >
          {{ formOpen ? 'Close form' : '+ Add card' }}
        </button>
        <p v-if="formOpen && editingCardId" class="mt-2 text-xs text-slate-500">
          Editing card — click another row or close to cancel.
        </p>
        <form
          v-if="formOpen"
          class="mt-4 max-w-lg space-y-4"
          @submit.prevent="onSubmitCard"
        >
          <div class="space-y-3">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {{ editingCardId ? 'Edit card' : 'New card' }} — Basic
            </p>
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
          </div>

          <div class="space-y-3 border-t border-slate-800 pt-4">
            <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">
              TOEIC / advanced (optional)
            </p>
            <div class="grid gap-3 sm:grid-cols-2">
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-400">Card type</label>
                <Field name="card_type" v-slot="{ field }">
                  <select
                    :name="field.name"
                    :value="field.value"
                    class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
                    @change="onCardTypeChange(field, $event)"
                  >
                    <option value="vocab">Vocab</option>
                    <option value="sentence">Sentence</option>
                    <option value="grammar">Grammar</option>
                  </select>
                </Field>
              </div>
              <div>
                <label class="mb-1 block text-xs font-medium text-slate-400">Language</label>
                <Field name="language" v-slot="{ field }">
                  <input
                    v-bind="field"
                    class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
                    placeholder="en"
                  />
                </Field>
              </div>
            </div>
            <div v-if="cardTypeLive === 'vocab'">
              <label class="mb-1 block text-xs font-medium text-slate-400">Part of speech</label>
              <Field name="part_of_speech" v-slot="{ field }">
                <select
                  v-bind="field"
                  class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
                >
                  <option
                    v-for="opt in partOfSpeechOptions"
                    :key="opt.value === '' ? '_empty' : opt.value"
                    :value="opt.value"
                  >
                    {{ opt.label }}
                  </option>
                </select>
              </Field>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-slate-400">Note</label>
              <Field name="note" v-slot="{ field }">
                <input
                  v-bind="field"
                  class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
                />
              </Field>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-slate-400">Example</label>
              <Field name="example" v-slot="{ field }">
                <input
                  v-bind="field"
                  class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none"
                />
              </Field>
            </div>
            <div>
              <label class="mb-1 block text-xs font-medium text-slate-400">Tags</label>
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="rounded-lg border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                  :disabled="tagSuggestLoading"
                  @click="runTagSuggest"
                >
                  {{ tagSuggestLoading ? 'Suggesting…' : 'Suggest tags (AI)' }}
                </button>
                <span v-if="tagSuggestMessage" class="text-xs text-slate-500">{{ tagSuggestMessage }}</span>
              </div>
              <div
                class="mt-2 flex max-h-32 flex-wrap gap-2 overflow-y-auto rounded-lg border border-slate-700 bg-slate-950 p-2"
              >
                <label
                  v-for="t in tags"
                  :key="t._id"
                  class="flex cursor-pointer items-center gap-1.5 text-xs text-slate-300"
                >
                  <input v-model="selectedTagIds" type="checkbox" :value="t._id" class="rounded border-slate-600" />
                  {{ t.name }}
                </label>
              </div>
              <div
                v-if="pendingNewTagNames.length"
                class="mt-2 rounded-lg border border-amber-900/40 bg-amber-950/20 px-2 py-2"
              >
                <p class="text-[10px] font-medium uppercase tracking-wide text-amber-200/80">
                  New tags (created when you save the card)
                </p>
                <div class="mt-1.5 flex flex-wrap gap-1.5">
                  <span
                    v-for="nm in pendingNewTagNames"
                    :key="nm"
                    class="inline-flex items-center gap-1 rounded-md border border-amber-800/60 bg-slate-950/50 px-2 py-0.5 text-xs text-amber-100/90"
                  >
                    {{ nm }}
                    <button
                      type="button"
                      class="rounded px-0.5 text-amber-300/80 hover:bg-amber-900/40 hover:text-amber-100"
                      aria-label="Remove suggested tag"
                      @click="removePendingNewTag(nm)"
                    >
                      ×
                    </button>
                  </span>
                </div>
              </div>
              <p class="mt-1 text-xs text-slate-500">
                AI matches existing tags only; new names are added when you save the card, not during suggest.
                Deck title is your content context.
              </p>
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
          </div>
          <button
            type="submit"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
          >
            {{ editingCardId ? 'Save changes' : 'Add card' }}
          </button>
        </form>
      </div>

      <ul class="mt-6 space-y-2">
        <li
          v-for="card in displayedCards"
          :key="card._id"
          class="flex flex-wrap items-center gap-2 rounded-lg border px-3 py-3 text-sm transition-colors sm:px-4"
          :class="
            editingCardId === card._id
              ? 'border-emerald-600/60 bg-emerald-950/20'
              : 'border-slate-800 bg-slate-900/30'
          "
        >
          <input
            type="checkbox"
            class="shrink-0 rounded border-slate-600"
            :checked="selectedCardIds.includes(card._id)"
            @click.stop
            @change="toggleCardSelection(card._id)"
          />
          <span
            class="min-w-0 flex-1 cursor-pointer text-slate-200 hover:opacity-90"
            role="button"
            tabindex="0"
            @click="openEditCard(card)"
            @keydown.enter.prevent="openEditCard(card)"
            @keydown.space.prevent="openEditCard(card)"
          >
            <span v-if="card.card_type" class="mr-2 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] uppercase text-slate-400">{{
              card.card_type
            }}</span>
            <span class="font-medium text-slate-100">{{ card.front?.content ?? '—' }}</span>
            <span class="mx-2 text-slate-600">→</span>
            <span class="text-slate-400">{{ card.back?.content ?? '—' }}</span>
            <span v-if="card.hint" class="ml-2 text-xs text-amber-500/90">· hint</span>
          </span>
          <button
            type="button"
            class="shrink-0 rounded-md p-1.5 text-slate-500 hover:bg-slate-800 hover:text-red-400"
            aria-label="Delete card"
            @click.stop="openDeleteCardsModal([card._id])"
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

    <ConfirmModal
      v-model="deleteCardsModalOpen"
      :title="deleteCardsModalTitle"
      :message="deleteCardsModalMessage"
      confirm-label="Delete"
      @confirm="executeDeleteCards"
    />
  </div>
</template>

<script setup lang="ts">
import Fuse from 'fuse.js'
import { Field, useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/yup'
import * as yup from 'yup'
import { Play, Search, Trash2 } from 'lucide-vue-next'
import { PART_OF_SPEECH_OPTIONS } from '~/constants/partOfSpeech'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

const route = useRoute()
const { api } = useApi()

type CardRow = {
  _id: string
  front?: { content?: string }
  back?: { content?: string }
  hint?: string
  note?: string
  example?: string
  card_type?: string
  part_of_speech?: string
  language?: string
  tag_ids?: string[]
}

const POS_VALUES = PART_OF_SPEECH_OPTIONS.map((o) => o.value).filter(Boolean)

const deck = ref<Record<string, unknown> | null>(null)
const cards = ref<CardRow[]>([])
const tags = ref<{ _id: string; name: string }[]>([])
const selectedTagIds = ref<string[]>([])
/** Form panel open (add or edit). */
const formOpen = ref(false)
/** When set, submit uses PATCH /cards/:id */
const editingCardId = ref<string | null>(null)
const pending = ref(true)
const searchQuery = ref('')
const cardTypeLive = ref('vocab')
const tagSuggestLoading = ref(false)
const tagSuggestMessage = ref('')
/** AI-suggested tag names not yet in DB; sent as new_tag_names on save. */
const pendingNewTagNames = ref<string[]>([])

type DeckStats = {
  study_records_total: number
  study_records_correct: number
  accuracy: number | null
  streak_max: number
  weak_topics: { tag_id: string; name: string; incorrect_count: number }[]
}

type WeakTagRow = { tag_id: string; name?: string; slug?: string; incorrect_count: number }

const deckStats = ref<DeckStats | null>(null)
const weakTags = ref<WeakTagRow[]>([])

const partOfSpeechOptions = PART_OF_SPEECH_OPTIONS

const cardSchema = toTypedSchema(
  yup.object({
    front: yup.string().min(1, 'Front is required').required(),
    back: yup.string().min(1, 'Back is required').required(),
    hint: yup.string().optional(),
    note: yup.string().optional(),
    example: yup.string().optional(),
    card_type: yup.string().oneOf(['vocab', 'sentence', 'grammar']).default('vocab'),
    part_of_speech: yup
      .string()
      .optional()
      .oneOf([...POS_VALUES, ''], 'Invalid part of speech'),
    language: yup.string().default('en'),
  }),
)

const cardFormInitial = {
  front: '',
  back: '',
  hint: '',
  note: '',
  example: '',
  card_type: 'vocab',
  part_of_speech: '',
  language: 'en',
}

const { handleSubmit, resetForm, values, setFieldValue } = useForm({
  validationSchema: cardSchema,
  initialValues: { ...cardFormInitial },
})

const fuse = computed(() =>
  new Fuse(cards.value, {
    keys: [
      { name: 'front.content', weight: 0.5 },
      { name: 'back.content', weight: 0.5 },
      'card_type',
      'note',
    ],
    threshold: 0.4,
  }),
)

const displayedCards = computed(() => {
  const q = searchQuery.value.trim()
  if (!q) return cards.value
  return fuse.value.search(q).map((r) => r.item)
})

const canStudy = computed(() => cards.value.length > 0)

const selectedCardIds = ref<string[]>([])
const deleteCardsModalOpen = ref(false)
const pendingDeleteCardIds = ref<string[]>([])

const allDisplayedCardsSelected = computed(() => {
  const rows = displayedCards.value
  return (
    rows.length > 0 && rows.every((c) => selectedCardIds.value.includes(c._id))
  )
})

const deleteCardsModalTitle = computed(() =>
  pendingDeleteCardIds.value.length > 1 ? 'Delete cards?' : 'Delete card?',
)

const deleteCardsModalMessage = computed(() => {
  const ids = pendingDeleteCardIds.value
  if (ids.length === 0) return ''
  if (ids.length === 1) {
    const c = cards.value.find((x) => x._id === ids[0])
    const front = c?.front?.content?.trim() || 'this card'
    return `Delete “${front.slice(0, 120)}${front.length > 120 ? '…' : ''}”? This cannot be undone.`
  }
  return `Delete ${ids.length} cards? This cannot be undone.`
})

watch(cards, (list) => {
  const idSet = new Set(list.map((c) => c._id))
  selectedCardIds.value = selectedCardIds.value.filter((id) => idSet.has(id))
})

function toggleCardSelection(id: string) {
  const s = new Set(selectedCardIds.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selectedCardIds.value = [...s]
}

function toggleSelectAllDisplayed() {
  const ids = displayedCards.value.map((c) => c._id)
  if (ids.length === 0) return
  if (allDisplayedCardsSelected.value) {
    selectedCardIds.value = selectedCardIds.value.filter((id) => !ids.includes(id))
  } else {
    selectedCardIds.value = [...new Set([...selectedCardIds.value, ...ids])]
  }
}

function clearCardSelection() {
  selectedCardIds.value = []
}

function openDeleteCardsModal(ids: string[]) {
  pendingDeleteCardIds.value = [...ids]
  deleteCardsModalOpen.value = true
}

async function executeDeleteCards() {
  const ids = [...pendingDeleteCardIds.value]
  pendingDeleteCardIds.value = []
  for (const id of ids) {
    try {
      await api(`/cards/${id}`, { method: 'DELETE' })
    } catch {
      /* continue with remaining ids */
    }
  }
  selectedCardIds.value = selectedCardIds.value.filter((id) => !ids.includes(id))
  if (editingCardId.value && ids.includes(editingCardId.value)) {
    formOpen.value = false
    resetCardFormState()
  }
  await fetchDeck()
  await loadDeckInsights()
}

async function loadTags() {
  try {
    const t = await api<{ tags: { _id: string; name: string }[] }>('/tags')
    tags.value = t.tags || []
  } catch {
    tags.value = []
  }
}

function resetCardFormState() {
  editingCardId.value = null
  resetForm({ values: { ...cardFormInitial } })
  cardTypeLive.value = 'vocab'
  selectedTagIds.value = []
  pendingNewTagNames.value = []
  tagSuggestMessage.value = ''
}

function removePendingNewTag(name: string) {
  pendingNewTagNames.value = pendingNewTagNames.value.filter((n) => n !== name)
}

function toggleAddForm() {
  formOpen.value = !formOpen.value
  if (formOpen.value) {
    resetCardFormState()
  }
}

function openEditCard(card: CardRow) {
  formOpen.value = true
  editingCardId.value = card._id
  const ct = card.card_type || 'vocab'
  cardTypeLive.value = ct
  resetForm({
    values: {
      front: card.front?.content ?? '',
      back: card.back?.content ?? '',
      hint: card.hint ?? '',
      note: card.note ?? '',
      example: card.example ?? '',
      card_type: ct === 'sentence' || ct === 'grammar' ? ct : 'vocab',
      part_of_speech: ct === 'vocab' ? (card.part_of_speech ?? '') : '',
      language: card.language ?? 'en',
    },
  })
  selectedTagIds.value = [...(card.tag_ids ?? [])]
  pendingNewTagNames.value = []
  tagSuggestMessage.value = ''
}

function onCardTypeChange(field: { value: unknown; onChange: (v: string) => void }, e: Event) {
  const v = (e.target as HTMLSelectElement).value
  field.onChange(v)
  cardTypeLive.value = v
  if (v !== 'vocab') {
    setFieldValue('part_of_speech', '')
  }
}

async function runTagSuggest() {
  const front = (values.front || '').trim()
  const back = (values.back || '').trim()
  if (!front) {
    tagSuggestMessage.value = 'Add front (and ideally back) first.'
    return
  }
  tagSuggestLoading.value = true
  tagSuggestMessage.value = ''
  try {
    const data = await api<{
      tags: { _id: string; name: string; slug?: string }[]
      pending_new?: { name: string; slug?: string }[]
    }>('/tags/suggest', {
      method: 'POST',
      body: {
        front,
        back: back || undefined,
        card_type: values.card_type || 'vocab',
        max_tags: 6,
        ...(values.card_type === 'vocab' && values.part_of_speech?.trim()
          ? { part_of_speech: values.part_of_speech.trim() }
          : {}),
      },
    })
    const ids = data.tags?.map((t) => t._id) ?? []
    const merged = new Set([...selectedTagIds.value, ...ids])
    selectedTagIds.value = [...merged]
    const pending = (data.pending_new ?? []).map((p) => p.name?.trim()).filter(Boolean) as string[]
    const seen = new Set(pendingNewTagNames.value.map((n) => n.toLowerCase()))
    for (const nm of pending) {
      const k = nm.toLowerCase()
      if (!seen.has(k)) {
        seen.add(k)
        pendingNewTagNames.value = [...pendingNewTagNames.value, nm]
      }
    }
    await loadTags()
    const pn = pending.length
    tagSuggestMessage.value =
      pn || ids.length
        ? `Matched ${ids.length} existing tag(s)${pn ? `; ${pn} new when you save` : ''}.`
        : 'No suggestions.'
  } catch (e: unknown) {
    const fe = e as { data?: { detail?: string } }
    tagSuggestMessage.value =
      typeof fe.data?.detail === 'string' ? fe.data.detail : 'Could not suggest tags'
  } finally {
    tagSuggestLoading.value = false
  }
}

async function fetchDeck() {
  pending.value = true
  try {
    const data = await api<{ deck: Record<string, unknown>; cards?: CardRow[] }>(
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

async function loadDeckInsights() {
  const id = route.params.id as string
  if (!id) {
    deckStats.value = null
    weakTags.value = []
    return
  }
  try {
    const [stats, weak] = await Promise.all([
      api<DeckStats>(`/learning/stats/summary?deck_id=${encodeURIComponent(id)}`),
      api<{ tags: WeakTagRow[] }>(`/learning/weak-tags?deck_id=${encodeURIComponent(id)}`),
    ])
    deckStats.value = stats
    weakTags.value = weak.tags || []
  } catch {
    deckStats.value = null
    weakTags.value = []
  }
}

function buildCardBody(formValues: Record<string, string | undefined>) {
  const body: Record<string, unknown> = {
    front: { content: formValues.front },
    back: { content: formValues.back },
    card_type: formValues.card_type || 'vocab',
    language: formValues.language || 'en',
    tag_ids: [...selectedTagIds.value],
    ...(pendingNewTagNames.value.length
      ? { new_tag_names: [...pendingNewTagNames.value] }
      : {}),
  }
  const n = formValues.note?.trim()
  const ex = formValues.example?.trim()
  const h = formValues.hint?.trim()
  if (n) body.note = n
  if (ex) body.example = ex
  if (h) body.hint = h
  if (formValues.card_type === 'vocab' && formValues.part_of_speech?.trim()) {
    body.part_of_speech = formValues.part_of_speech.trim()
  }
  return body
}

const onSubmitCard = handleSubmit(async (formValues) => {
  const body = buildCardBody(formValues)
  const eid = editingCardId.value
  if (eid) {
    await api(`/cards/${eid}`, { method: 'PATCH', body })
  } else {
    await api(`/decks/${route.params.id}/cards`, { method: 'POST', body })
  }
  formOpen.value = false
  resetCardFormState()
  await fetchDeck()
  await loadDeckInsights()
})

onMounted(async () => {
  await loadTags()
  await fetchDeck()
  await loadDeckInsights()
})
watch(
  () => route.params.id as string,
  async (id, prevId) => {
    if (prevId !== undefined && prevId !== id) {
      formOpen.value = false
      resetCardFormState()
      selectedCardIds.value = []
    }
    await fetchDeck()
    await loadDeckInsights()
  },
)

</script>
