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
        <h2 class="text-xl font-semibold text-white">Simple study</h2>
        <p v-if="sessionId && !done" class="text-sm text-slate-400">
          Remaining: {{ remaining }}
        </p>
      </div>
      <p class="mt-1 text-sm text-slate-400">
        Show the back, then mark Remembered or Forgot. Forgotten cards go to the end of the queue.
      </p>

      <p v-if="error" class="mt-4 text-sm text-red-400">{{ error }}</p>

      <div v-if="!sessionId && !done" class="mt-6">
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
          :disabled="starting"
          @click="startSession"
        >
          {{ starting ? 'Starting…' : 'Start' }}
        </button>
      </div>

      <div v-else-if="done" class="mt-8 rounded-xl border border-slate-800 bg-slate-900/50 p-6 text-center">
        <h3 class="text-lg font-medium text-white">Session complete</h3>
        <p v-if="summary" class="mt-2 text-sm text-slate-400">
          Cleared {{ summary.total_cards }} cards ·
          Remembered {{ summary.remembered }} ·
          Forgot events {{ summary.forgot_events }}
        </p>
        <div class="mt-4 flex flex-wrap justify-center gap-2">
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

      <div v-else-if="card" class="mt-6 max-w-xl">
        <SimpleFlashcard
          :front="card.front"
          :back="card.back"
          :show-back="showBack"
          @flip="showBack = !showBack"
        />
        <div v-if="showBack" class="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-lg border border-amber-800/70 bg-amber-950/30 px-4 py-2 text-sm font-medium text-amber-100 hover:bg-amber-950/50"
            :disabled="grading"
            @click="grade(false)"
          >
            Forgot
          </button>
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
            :disabled="grading"
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

const route = useRoute()
const { api } = useApi()
const deckId = computed(() => String(route.query.deck_id || ''))

const sessionId = ref('')
const card = ref<SimpleCard | null>(null)
const remaining = ref(0)
const showBack = ref(false)
const starting = ref(false)
const grading = ref(false)
const done = ref(false)
const error = ref('')
const summary = ref<{
  total_cards: number
  remembered: number
  forgot_events: number
} | null>(null)
const shownAt = ref(0)

function applyCard(next: SimpleCard | null | undefined, rem: number) {
  card.value = next ?? null
  remaining.value = rem
  showBack.value = false
  shownAt.value = Date.now()
}

async function startSession() {
  if (!deckId.value) return
  error.value = ''
  starting.value = true
  done.value = false
  summary.value = null
  try {
    const data = await api<{
      session_id: string
      remaining: number
      card: SimpleCard | null
    }>('/simple/learning/sessions', {
      method: 'POST',
      body: { deck_id: deckId.value },
    })
    sessionId.value = data.session_id
    applyCard(data.card, data.remaining)
  } catch (e: unknown) {
    const err = e as { data?: { detail?: string } }
    error.value = err?.data?.detail || 'Failed to start session'
  } finally {
    starting.value = false
  }
}

async function grade(remembered: boolean) {
  if (!sessionId.value || !card.value || grading.value) return
  grading.value = true
  error.value = ''
  const time_ms = Math.max(0, Date.now() - shownAt.value)
  try {
    const data = await api<{
      done: boolean
      remaining: number
      card: SimpleCard | null
      summary?: { total_cards: number; remembered: number; forgot_events: number }
    }>(`/simple/learning/sessions/${sessionId.value}/grade`, {
      method: 'POST',
      body: { card_id: card.value._id, remembered, time_ms },
    })
    if (data.done) {
      done.value = true
      summary.value = data.summary ?? null
      card.value = null
      remaining.value = 0
    } else {
      applyCard(data.card, data.remaining)
    }
  } catch {
    error.value = 'Failed to save grade'
  } finally {
    grading.value = false
  }
}

async function restart() {
  sessionId.value = ''
  card.value = null
  done.value = false
  summary.value = null
  await startSession()
}

watch(
  deckId,
  (id) => {
    sessionId.value = ''
    card.value = null
    done.value = false
    summary.value = null
    error.value = ''
    if (id) startSession()
  },
  { immediate: true },
)
</script>
