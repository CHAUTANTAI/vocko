<template>
  <div>
    <NuxtLink to="/deck" class="text-sm text-slate-400 hover:text-emerald-400">← Decks</NuxtLink>

    <div v-if="!deckId" class="mt-8 rounded-xl border border-amber-900/50 bg-amber-950/30 p-6 text-center">
      <p class="text-amber-200/90">Choose a deck to study.</p>
      <NuxtLink
        to="/deck"
        class="mt-4 inline-block rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
      >
        Go to decks
      </NuxtLink>
    </div>

    <div v-else class="mt-6">
      <h2 class="text-xl font-semibold text-white">Study session</h2>
      <p class="mt-1 text-sm text-slate-400">Answer from the card back (exact match, case insensitive).</p>

      <div class="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm"
          :class="
            mode === 'learn'
              ? 'bg-emerald-600 text-white'
              : 'border border-slate-600 text-slate-300 hover:bg-slate-800'
          "
          @click="mode = 'learn'"
        >
          Learn
        </button>
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm"
          :class="
            mode === 'review'
              ? 'bg-emerald-600 text-white'
              : 'border border-slate-600 text-slate-300 hover:bg-slate-800'
          "
          @click="mode = 'review'"
        >
          Review due
        </button>
      </div>

      <div v-if="!sessionId" class="mt-6">
        <button
          type="button"
          class="rounded-lg bg-emerald-600 px-5 py-2.5 font-medium text-white hover:bg-emerald-500"
          @click="startSession"
        >
          Start session
        </button>
        <p v-if="sessionError" class="mt-2 text-sm text-red-400">{{ sessionError }}</p>
      </div>

      <div v-else class="mt-6">
        <div v-if="question">
          <ClientOnly>
            <div
              v-motion
              :key="question.card_id"
              :initial="{ opacity: 0, y: 8 }"
              :enter="{ opacity: 1, y: 0, transition: { duration: 280 } }"
              class="rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-950 p-8 text-center shadow-lg"
            >
              <p class="text-xs uppercase tracking-wide text-slate-500">Prompt</p>
              <p class="mt-3 text-xl font-medium text-white">{{ questionFront }}</p>
            </div>
            <template #fallback>
              <div class="rounded-xl border border-slate-700 bg-slate-900 p-8 text-center text-lg text-white">
                {{ questionFront }}
              </div>
            </template>
          </ClientOnly>

          <div class="mt-6 space-y-3">
            <input
              v-model="answer"
              type="text"
              class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder="Your answer"
              @keyup.enter="submit"
            />
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
                @click="submit"
              >
                Submit
              </button>
            </div>
            <p v-if="resultLabel" class="text-sm" :class="resultOk ? 'text-emerald-400' : 'text-red-400'">
              {{ resultLabel }}
            </p>
          </div>
        </div>

        <div v-else class="rounded-xl border border-slate-800 bg-slate-900/50 p-8 text-center">
          <p class="text-lg text-slate-200">Queue finished</p>
          <p v-if="summary" class="mt-2 text-sm text-slate-400">
            {{ summary.correct }} / {{ summary.questions }} correct ({{
              Math.round((summary.accuracy || 0) * 100)
            }}%)
          </p>
          <button
            type="button"
            class="mt-6 rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
            @click="resetSession"
          >
            New session
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

const route = useRoute()
const { api } = useApi()

type Q = { card_id: string; front?: { content?: string }; question_type?: string }

const deckId = computed(() => (route.query.deck_id as string) || '')
const mode = ref<'learn' | 'review'>('learn')
const sessionId = ref('')
const question = ref<Q | null>(null)
const answer = ref('')
const resultLabel = ref('')
const resultOk = ref(false)
const sessionError = ref('')
const summary = ref<{ questions: number; correct: number; accuracy: number } | null>(null)

const questionFront = computed(() => question.value?.front?.content ?? '—')

async function startSession() {
  sessionError.value = ''
  summary.value = null
  answer.value = ''
  resultLabel.value = ''
  try {
    const data = await api<{ session_id: string; preloaded_questions: Q[] }>('/learning/sessions', {
      method: 'POST',
      body: {
        deck_id: deckId.value,
        mode: mode.value,
        options: { queue_size: 30 },
      },
    })
    sessionId.value = data.session_id
    const first = data.preloaded_questions?.[0]
    question.value = first || null
    if (!first) {
      sessionError.value = 'No cards in queue for this mode. Try Learn or add cards.'
      sessionId.value = ''
    }
  } catch {
    sessionError.value = 'Could not start session'
  }
}

async function getNext() {
  const data = await api<{ question: Q | null }>(`/learning/sessions/${sessionId.value}/next`)
  question.value = data.question
  answer.value = ''
  resultLabel.value = ''
  if (!data.question) {
    await finish()
  }
}

async function submit() {
  if (!question.value) return
  try {
    const data = await api<{ result: string }>(`/learning/sessions/${sessionId.value}/answer`, {
      method: 'POST',
      body: { card_id: question.value.card_id, response: answer.value },
    })
    resultOk.value = data.result === 'correct'
    resultLabel.value = data.result === 'correct' ? 'Correct' : 'Incorrect'
    await getNext()
  } catch {
    resultLabel.value = 'Submit failed'
    resultOk.value = false
  }
}

async function finish() {
  if (!sessionId.value) return
  try {
    const data = await api<{ summary: { questions: number; correct: number; accuracy: number } }>(
      `/learning/sessions/${sessionId.value}/finish`,
      { method: 'POST' },
    )
    summary.value = data.summary
  } catch {
    summary.value = null
  }
  question.value = null
}

function resetSession() {
  sessionId.value = ''
  question.value = null
  summary.value = null
  sessionError.value = ''
}
</script>
