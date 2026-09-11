<template>
  <div>
    <div class="flex flex-wrap items-center gap-4">
      <NuxtLink
        :to="deckId ? `/simple/${deckId}` : '/simple'"
        class="text-sm text-slate-400 hover:text-emerald-400"
      >
        ← Back to deck
      </NuxtLink>
      <NuxtLink to="/simple" class="text-sm text-slate-400 hover:text-emerald-400">All simple decks</NuxtLink>
    </div>

    <div
      v-if="!deckId"
      class="mt-8 rounded-xl border border-amber-900/50 bg-amber-950/30 p-6 text-center"
    >
      <p class="text-amber-200/90">Choose a simple deck to study.</p>
      <NuxtLink
        to="/simple"
        class="mt-4 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
      >
        Go to Simple
      </NuxtLink>
    </div>

    <div v-else class="mt-6">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-xl font-semibold text-white">
          {{ isQuick5 ? 'Ôn nhanh 5 phút' : 'Simple study' }}
        </h2>
        <p v-if="active && !done" class="text-sm text-slate-400">
          Remaining: {{ queue.length }}
        </p>
      </div>
      <p class="mt-1 text-sm text-slate-400">
        <template v-if="isQuick5">
          Ưu tiên thẻ có điểm yếu cao (số quên − số nhớ). Tối đa ~12 thẻ.
        </template>
        <template v-else>
          Grades stay local until the session ends — then stats sync in one request.
        </template>
      </p>

      <p v-if="error" class="mt-4 text-sm text-red-400">{{ error }}</p>
      <p v-if="syncing" class="mt-2 text-sm text-slate-400">Saving session…</p>

      <div v-if="!active && !done" class="mt-6 flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
          :disabled="starting"
          @click="startSession('all')"
        >
          {{ starting && pendingMode === 'all' ? 'Starting…' : 'Start full deck' }}
        </button>
        <button
          type="button"
          class="rounded-lg border border-amber-800/70 bg-amber-950/30 px-4 py-2 text-sm font-medium text-amber-100 hover:bg-amber-950/50"
          :disabled="starting"
          @click="startSession('quick_5')"
        >
          {{ starting && pendingMode === 'quick_5' ? 'Starting…' : 'Ôn 5 phút (thẻ yếu)' }}
        </button>
      </div>

      <div v-else-if="done" class="mt-8 rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center">
        <h3 class="text-lg font-medium text-white">Session complete</h3>
        <p v-if="summary" class="mt-2 text-sm text-slate-400">
          Cleared {{ summary.total_cards }} cards ·
          Remembered {{ summary.remembered }} ·
          Forgot events {{ summary.forgot_events }}
        </p>
        <div v-if="needsRetry" class="mt-4">
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
            :disabled="syncing"
            @click="flushComplete"
          >
            {{ syncing ? 'Saving…' : 'Retry save stats' }}
          </button>
        </div>
        <div v-else class="mt-4 flex flex-wrap justify-center gap-2">
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
            @click="restart"
          >
            Study again
          </button>
          <NuxtLink
            :to="`/simple/${deckId}`"
            class="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
          >
            Back to deck
          </NuxtLink>
        </div>
      </div>

      <div v-else-if="current" class="mt-6 max-w-xl">
        <SimpleFlashcard
          :front="current.front"
          :back="current.back"
          :show-back="showBack"
          @flip="showBack = !showBack"
        />
        <div v-if="showBack" class="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-lg border border-amber-800/70 bg-amber-950/30 px-4 py-2 text-sm font-medium text-amber-100 hover:bg-amber-950/50"
            :disabled="syncing"
            @click="grade(false)"
          >
            Forgot
          </button>
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
            :disabled="syncing"
            @click="grade(true)"
          >
            Remembered
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

type SimpleCard = { _id: string; front: string; back: string }
type StudyEvent = { card_id: string; remembered: boolean; time_ms: number }

const route = useRoute()
const { api } = useApi()
const deckId = computed(() => String(route.query.deck_id || ''))
const queryMode = computed(() => {
  const m = String(route.query.mode || 'all').toLowerCase()
  return m === 'quick_5' ? 'quick_5' : 'all'
})

const sessionId = ref('')
const sessionMode = ref<'all' | 'quick_5'>('all')
const pendingMode = ref<'all' | 'quick_5' | null>(null)
const queue = ref<SimpleCard[]>([])
const events = ref<StudyEvent[]>([])
const initialCount = ref(0)
const showBack = ref(false)
const starting = ref(false)
const syncing = ref(false)
const done = ref(false)
const needsRetry = ref(false)
const active = ref(false)
const error = ref('')
const summary = ref<{
  total_cards: number
  remembered: number
  forgot_events: number
} | null>(null)
const shownAt = ref(0)

const current = computed(() => queue.value[0] ?? null)
const isQuick5 = computed(() => sessionMode.value === 'quick_5')

function showFront() {
  showBack.value = false
  shownAt.value = Date.now()
}

function applyGradeLocal(cardId: string, remembered: boolean) {
  const q = queue.value
  if (!q.length || q[0]._id !== cardId) return
  const rest = q.slice(1)
  if (remembered) {
    queue.value = rest
  } else {
    queue.value = [...rest, q[0]]
  }
}

function localSummary() {
  return {
    total_cards: initialCount.value,
    remembered: events.value.filter((e) => e.remembered).length,
    forgot_events: events.value.filter((e) => !e.remembered).length,
  }
}

async function flushComplete() {
  if (!sessionId.value || syncing.value) return
  syncing.value = true
  error.value = ''
  try {
    const data = await api<{
      summary: { total_cards: number; remembered: number; forgot_events: number }
    }>(`/simple/learning/sessions/${sessionId.value}/complete`, {
      method: 'POST',
      body: { events: events.value },
    })
    summary.value = data.summary ?? localSummary()
    needsRetry.value = false
    done.value = true
    active.value = false
  } catch {
    error.value = 'Failed to save session stats'
    summary.value = localSummary()
    needsRetry.value = true
    done.value = true
    active.value = false
  } finally {
    syncing.value = false
  }
}

async function startSession(mode: 'all' | 'quick_5' = queryMode.value) {
  if (!deckId.value) return
  error.value = ''
  starting.value = true
  pendingMode.value = mode
  done.value = false
  needsRetry.value = false
  summary.value = null
  events.value = []
  try {
    const data = await api<{
      session_id: string
      mode?: string
      initial_count: number
      cards: SimpleCard[]
    }>('/simple/learning/sessions', {
      method: 'POST',
      body: { deck_id: deckId.value, mode },
    })
    sessionId.value = data.session_id
    sessionMode.value = data.mode === 'quick_5' ? 'quick_5' : mode
    const cards = data.cards ?? []
    queue.value = cards
    initialCount.value = data.initial_count ?? cards.length
    active.value = true
    showFront()
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    error.value = err?.data?.detail || 'Failed to start session'
    active.value = false
    sessionMode.value = mode
  } finally {
    starting.value = false
    pendingMode.value = null
  }
}

async function grade(remembered: boolean) {
  const card = current.value
  if (!card || !active.value || syncing.value) return
  const time_ms = Math.max(0, Date.now() - shownAt.value)
  events.value.push({ card_id: card._id, remembered, time_ms })
  applyGradeLocal(card._id, remembered)
  if (!queue.value.length) {
    await flushComplete()
  } else {
    showFront()
  }
}

async function restart() {
  sessionId.value = ''
  queue.value = []
  events.value = []
  done.value = false
  needsRetry.value = false
  summary.value = null
  active.value = false
  await startSession(sessionMode.value)
}

watch(
  deckId,
  (id) => {
    sessionId.value = ''
    queue.value = []
    events.value = []
    done.value = false
    needsRetry.value = false
    summary.value = null
    active.value = false
    error.value = ''
    if (id) startSession(queryMode.value)
  },
  { immediate: true },
)
</script>
