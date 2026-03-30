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
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-xl font-semibold text-white">Study session</h2>
        <p v-if="sessionId && sessionAnswered > 0" class="text-sm text-slate-400">
          Score: {{ sessionCorrect }} / {{ sessionAnswered }} correct
        </p>
      </div>
      <p class="mt-1 text-sm text-slate-400">
        Exact match (case insensitive), one typo accepted, or AI grading if configured.
      </p>

      <div class="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          class="rounded-lg px-3 py-1.5 text-sm"
          :class="
            mode === 'learn'
              ? 'bg-emerald-600 text-white'
              : 'border border-slate-600 text-slate-300 hover:bg-slate-800'
          "
          :disabled="!!sessionId"
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
          :disabled="!!sessionId"
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
          <div class="relative">
            <label
              class="absolute right-2 top-2 z-20 flex cursor-pointer select-none items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-900/90 px-2 py-1 text-xs text-slate-300"
            >
              <span>Auto next</span>
              <button
                type="button"
                role="switch"
                :aria-checked="autoAdvance"
                class="relative h-5 w-9 rounded-full transition-colors"
                :class="autoAdvance ? 'bg-emerald-600' : 'bg-slate-600'"
                @click="autoAdvance = !autoAdvance"
              >
                <span
                  class="absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform"
                  :class="autoAdvance ? 'left-4' : 'left-0.5'"
                />
              </button>
            </label>
            <ClientOnly>
              <div
                v-motion
                :key="question.card_id"
                :initial="{ opacity: 0, y: 8 }"
                :enter="{ opacity: 1, y: 0, transition: { duration: 280 } }"
                class="rounded-xl border border-slate-700 shadow-lg [perspective:1200px]"
              >
                <button
                  type="button"
                  class="relative w-full min-h-[11rem] rounded-xl text-left outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/60 disabled:cursor-default"
                  :disabled="!canFlipCard"
                  :class="canFlipCard ? 'cursor-pointer' : 'cursor-default'"
                  :aria-label="canFlipCard ? 'Flip card to see answer' : 'Card prompt'"
                  @click="toggleCardFlip"
                >
                  <div
                    class="relative h-full min-h-[11rem] w-full transition-transform duration-500 ease-out"
                    :style="{
                      transformStyle: 'preserve-3d',
                      transform: cardFlipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                    }"
                  >
                    <div
                      class="absolute inset-0 flex flex-col justify-center rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-950 p-8 pt-12 text-center shadow-inner [backface-visibility:hidden]"
                    >
                      <p class="text-xs uppercase tracking-wide text-slate-500">Prompt</p>
                      <p class="mt-3 text-xl font-medium text-white">{{ questionFront }}</p>
                      <p
                        v-if="canFlipCard"
                        class="mt-4 text-xs text-slate-500"
                      >
                        Tap card to see the answer
                      </p>
                    </div>
                    <div
                      class="absolute inset-0 flex flex-col justify-center rounded-xl border border-emerald-900/40 bg-gradient-to-br from-slate-900 to-emerald-950/30 p-8 pt-12 text-center shadow-inner [backface-visibility:hidden] [transform:rotateY(180deg)]"
                    >
                      <p class="text-xs uppercase tracking-wide text-emerald-500/80">Answer</p>
                      <p class="mt-3 text-xl font-medium text-emerald-50">
                        {{ revealedBack?.content ?? '—' }}
                      </p>
                      <p
                        v-if="canFlipCard"
                        class="mt-4 text-xs text-slate-500"
                      >
                        Tap card to return to prompt
                      </p>
                    </div>
                  </div>
                </button>
              </div>
              <template #fallback>
                <div class="rounded-xl border border-slate-700 bg-slate-900 p-8 pt-12 text-center text-lg text-white">
                  {{ questionFront }}
                </div>
              </template>
            </ClientOnly>
          </div>

          <div
            v-if="progressVisible"
            class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800"
            aria-hidden="true"
          >
            <div
              :key="progressBarKey"
              class="session-progress-bar h-full w-full origin-left rounded-full bg-emerald-500"
            />
          </div>

          <div class="mt-6 space-y-3">
            <input
              v-model="answer"
              type="text"
              class="w-full max-w-md rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-60"
              placeholder="Your answer"
              :disabled="inputLocked"
              @keyup.enter="onEnterAnswer"
            />
            <div v-if="gradedRoundActive && submittedDisplay" class="max-w-md text-sm text-slate-400">
              <span class="text-slate-500">Your answer: </span>
              <span class="font-mono text-slate-200">
                <template v-if="answerDisplayPieces">
                  <template v-for="(p, idx) in answerDisplayPieces" :key="idx">
                    <span
                      v-if="p.gap"
                      class="inline-block min-w-[0.35rem] border-b-2 border-amber-400 text-amber-400/90"
                      title="Missing character"
                      >&#8203;</span
                    >
                    <span v-else-if="p.ch !== undefined">{{ p.ch }}</span>
                  </template>
                </template>
                <template v-else>
                  <span v-for="(ch, i) in submittedDisplay" :key="i" :class="charHighlightClass(i)">{{ ch }}</span>
                </template>
              </span>
            </div>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="inline-flex min-w-[5.5rem] items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="submitLoading || gradedRoundActive"
                  @click="submit"
                >
                  {{ submitLoading ? '…' : 'Submit' }}
                </button>
                <button
                  type="button"
                  class="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                  :disabled="hintLoading || gradedRoundActive"
                  @click="fetchHint"
                >
                  <Lightbulb class="h-4 w-4 text-amber-400" aria-hidden="true" />
                  {{ hintLoading ? 'Hint…' : 'Hint' }}
                </button>
              </div>
              <button
                type="button"
                class="inline-flex items-center gap-1 rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                :disabled="!canClickNext || submitLoading"
                @click="doAdvance"
              >
                Next
                <ChevronRight class="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
            <div
              v-if="hintPanelOpen && (hintText || hintError)"
              class="rounded-lg border border-amber-900/40 bg-amber-950/20 px-3 py-2 text-sm text-amber-100/90"
            >
              <div class="flex items-start justify-between gap-2">
                <p class="flex-1">{{ hintError || hintText }}</p>
                <button
                  type="button"
                  class="shrink-0 text-xs text-slate-400 hover:text-white"
                  @click="hintPanelOpen = false"
                >
                  Hide
                </button>
              </div>
            </div>
            <p v-if="resultLabel" class="text-sm" :class="resultOk ? 'text-emerald-400' : 'text-red-400'">
              {{ resultLabel }}
            </p>
            <p v-if="resultNote" class="text-xs text-slate-500">{{ resultNote }}</p>
          </div>
        </div>

        <div v-else class="rounded-xl border border-slate-800 bg-slate-900/50 p-8">
          <p class="text-center text-lg text-slate-200">Queue finished</p>
          <p v-if="summary" class="mt-2 text-center text-sm text-slate-400">
            {{ summary.correct }} / {{ summary.questions }} correct ({{
              Math.round((summary.accuracy || 0) * 100)
            }}%)
          </p>
          <ul v-if="reviewItems.length" class="mt-6 max-h-80 space-y-2 overflow-y-auto text-left text-sm">
            <li
              v-for="row in reviewItems"
              :key="row.card_id"
              class="rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2"
            >
              <div class="flex flex-wrap items-start justify-between gap-2">
                <div class="min-w-0 flex-1 text-slate-200">
                  <span class="font-medium text-slate-100">{{ row.front?.content ?? '—' }}</span>
                  <span class="mx-1 text-slate-600">→</span>
                  <span class="text-slate-400">{{ row.back?.content ?? '—' }}</span>
                </div>
                <span
                  class="shrink-0 rounded px-2 py-0.5 text-xs font-medium"
                  :class="
                    row.result === 'correct'
                      ? 'bg-emerald-900/50 text-emerald-300'
                      : 'bg-red-900/40 text-red-300'
                  "
                >
                  {{ row.result === 'correct' ? 'Correct' : 'Wrong' }}
                </span>
              </div>
              <p v-if="row.response" class="mt-1 text-xs text-slate-500">
                You: <span class="text-slate-400">{{ row.response }}</span>
                <span v-if="row.match_type" class="text-slate-600"> · {{ row.match_type }}</span>
              </p>
            </li>
          </ul>
          <div class="mt-6 text-center">
            <button
              type="button"
              class="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
              @click="resetSession"
            >
              New session
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight, Lightbulb } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

const AUTO_KEY = 'vocko-learning-auto-advance'

const route = useRoute()
const { api } = useApi()

type TypoHighlight = {
  start: number
  end: number
  kind: 'substitute' | 'insert' | 'delete'
}

type Q = {
  card_id: string
  front?: { content?: string }
  question_type?: string
  has_stored_hint?: boolean
}

type ReviewItem = {
  card_id: string
  front?: { content?: string }
  back?: { content?: string }
  result?: string
  response?: string
  match_type?: string
  note?: string
  typo_highlight?: TypoHighlight
}

type AnswerApi = {
  result: string
  match_type?: string
  note?: string
  typo_highlight?: TypoHighlight
  session_answered?: number
  session_correct?: number
  card_back?: { content?: string }
}

const deckId = computed(() => (route.query.deck_id as string) || '')
const mode = ref<'learn' | 'review'>('learn')
const sessionId = ref('')
const question = ref<Q | null>(null)
const answer = ref('')
const resultLabel = ref('')
const resultOk = ref(false)
const sessionError = ref('')
const summary = ref<{ questions: number; correct: number; accuracy: number } | null>(null)
const reviewItems = ref<ReviewItem[]>([])

const hintText = ref('')
const hintError = ref('')
const hintLoading = ref(false)
const hintPanelOpen = ref(false)
const resultNote = ref('')

const autoAdvance = ref(true)
const submitLoading = ref(false)
const gradedRoundActive = ref(false)
const submittedDisplay = ref('')
const typoHighlight = ref<TypoHighlight | null>(null)
const canClickNext = ref(false)
const progressVisible = ref(false)
const progressBarKey = ref(0)
const cardFlipped = ref(false)
const revealedBack = ref<{ content?: string } | null>(null)
const sessionAnswered = ref(0)
const sessionCorrect = ref(0)

let advanceTimerId: ReturnType<typeof setTimeout> | null = null

const questionFront = computed(() => question.value?.front?.content ?? '—')

const canFlipCard = computed(
  () => gradedRoundActive.value && revealedBack.value != null,
)

const inputLocked = computed(() => submitLoading.value || gradedRoundActive.value)

const answerDisplayPieces = computed(() => {
  const text = submittedDisplay.value
  const hl = typoHighlight.value
  if (!hl || !text || hl.kind !== 'delete' || hl.start !== hl.end) return null
  const pieces: Array<{ ch?: string; gap?: boolean }> = []
  const n = text.length
  const j = hl.start
  for (let i = 0; i < n; i++) {
    if (i === j) pieces.push({ gap: true })
    pieces.push({ ch: text[i]! })
  }
  if (j === n) pieces.push({ gap: true })
  return pieces
})

function charHighlightClass(index: number) {
  const hl = typoHighlight.value
  if (!hl || hl.kind === 'delete') return ''
  if (index >= hl.start && index < hl.end) return 'rounded bg-amber-500/35 text-amber-100'
  return ''
}

function cancelAdvanceTimer() {
  if (advanceTimerId !== null) {
    clearTimeout(advanceTimerId)
    advanceTimerId = null
  }
}

function clearGradeUi() {
  gradedRoundActive.value = false
  submittedDisplay.value = ''
  typoHighlight.value = null
  resultLabel.value = ''
  resultNote.value = ''
  resultOk.value = false
  canClickNext.value = false
  progressVisible.value = false
  cardFlipped.value = false
  revealedBack.value = null
}

function toggleCardFlip() {
  if (!canFlipCard.value) return
  cardFlipped.value = !cardFlipped.value
}

function clearHintForCard() {
  hintText.value = ''
  hintError.value = ''
  hintPanelOpen.value = false
}

onMounted(() => {
  if (import.meta.client) {
    const v = localStorage.getItem(AUTO_KEY)
    if (v === '0') autoAdvance.value = false
    if (v === '1') autoAdvance.value = true
  }
})

watch(autoAdvance, (on) => {
  if (import.meta.client) localStorage.setItem(AUTO_KEY, on ? '1' : '0')
})

onUnmounted(() => {
  cancelAdvanceTimer()
})

async function startSession() {
  sessionError.value = ''
  summary.value = null
  reviewItems.value = []
  answer.value = ''
  clearGradeUi()
  cancelAdvanceTimer()
  sessionAnswered.value = 0
  sessionCorrect.value = 0
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
    clearHintForCard()
    if (!first) {
      sessionError.value = 'No cards in queue for this mode. Try Learn or add cards.'
      sessionId.value = ''
    }
  } catch {
    sessionError.value = 'Could not start session'
  }
}

async function getNext() {
  cancelAdvanceTimer()
  clearGradeUi()
  const data = await api<{ question: Q | null }>(`/learning/sessions/${sessionId.value}/next`)
  question.value = data.question
  answer.value = ''
  clearHintForCard()
  if (!data.question) {
    await finish()
  }
}

async function fetchHint() {
  if (!sessionId.value || !question.value || gradedRoundActive.value) return
  hintLoading.value = true
  hintError.value = ''
  hintPanelOpen.value = true
  try {
    const data = await api<{ hint: string; source: string }>(
      `/learning/sessions/${sessionId.value}/hint`,
      {
        method: 'POST',
        body: { card_id: question.value.card_id },
      },
    )
    hintText.value = data.hint
  } catch (e: unknown) {
    const fe = e as { data?: { detail?: string | { msg?: string }[] } }
    const d = fe.data?.detail
    hintText.value = ''
    if (typeof d === 'string') hintError.value = d
    else if (Array.isArray(d))
      hintError.value = d.map((x) => x.msg ?? '').filter(Boolean).join(' ') || 'Could not load hint'
    else hintError.value = 'Could not load hint'
  } finally {
    hintLoading.value = false
  }
}

function scheduleAdvanceAfterGrade() {
  cancelAdvanceTimer()
  gradedRoundActive.value = true
  canClickNext.value = false
  cardFlipped.value = false
  progressVisible.value = true
  progressBarKey.value += 1
  advanceTimerId = setTimeout(() => {
    advanceTimerId = null
    if (autoAdvance.value) void doAdvance()
    else canClickNext.value = true
  }, 2000)
}

async function doAdvance() {
  cancelAdvanceTimer()
  clearGradeUi()
  await getNext()
}

function onEnterAnswer() {
  if (!gradedRoundActive.value && !submitLoading.value) void submit()
}

async function submit() {
  if (!question.value || submitLoading.value || gradedRoundActive.value) return
  submitLoading.value = true
  try {
    const data = await api<AnswerApi>(`/learning/sessions/${sessionId.value}/answer`, {
      method: 'POST',
      body: { card_id: question.value.card_id, response: answer.value },
    })
    resultOk.value = data.result === 'correct'
    if (data.result === 'correct') {
      if (data.match_type === 'llm') resultLabel.value = 'Correct (close match)'
      else if (data.match_type === 'typo_one') resultLabel.value = 'Correct (one typo)'
      else resultLabel.value = 'Correct'
    } else {
      resultLabel.value = 'Incorrect'
    }
    const parts: string[] = []
    if (data.match_type === 'llm' && data.result === 'correct') parts.push('Graded with AI')
    if (data.note) parts.push(data.note)
    resultNote.value = parts.join(' · ')

    if (typeof data.session_answered === 'number') sessionAnswered.value = data.session_answered
    if (typeof data.session_correct === 'number') sessionCorrect.value = data.session_correct

    submittedDisplay.value = answer.value.trim()
    typoHighlight.value =
      data.match_type === 'typo_one' && data.typo_highlight ? data.typo_highlight : null

    revealedBack.value = data.card_back ?? { content: undefined }

    scheduleAdvanceAfterGrade()
  } catch {
    resultLabel.value = 'Submit failed'
    resultOk.value = false
    resultNote.value = ''
  } finally {
    submitLoading.value = false
  }
}

async function finish() {
  if (!sessionId.value) return
  try {
    const data = await api<{
      summary: { questions: number; correct: number; accuracy: number }
      items?: ReviewItem[]
    }>(`/learning/sessions/${sessionId.value}/finish`, { method: 'POST' })
    summary.value = data.summary
    reviewItems.value = data.items ?? []
  } catch {
    summary.value = null
    reviewItems.value = []
  }
  question.value = null
}

function resetSession() {
  cancelAdvanceTimer()
  sessionId.value = ''
  question.value = null
  summary.value = null
  reviewItems.value = []
  sessionError.value = ''
  clearHintForCard()
  clearGradeUi()
  sessionAnswered.value = 0
  sessionCorrect.value = 0
}
</script>

<style scoped>
@keyframes session-progress-linear {
  from {
    transform: scaleX(0);
  }
  to {
    transform: scaleX(1);
  }
}

.session-progress-bar {
  transform: scaleX(0);
  transform-origin: left center;
  animation: session-progress-linear 2s linear forwards;
  will-change: transform;
}
</style>
