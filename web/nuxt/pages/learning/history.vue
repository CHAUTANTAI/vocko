<template>
  <div>
    <div class="flex flex-wrap items-center gap-4">
      <NuxtLink to="/deck" class="text-sm text-slate-400 hover:text-emerald-400">← Decks</NuxtLink>
      <NuxtLink
        :to="`/learning/session${deckFilter ? `?deck_id=${encodeURIComponent(deckFilter)}` : ''}`"
        class="text-sm text-slate-400 hover:text-emerald-400"
      >
        Study
      </NuxtLink>
    </div>
    <h1 class="mt-4 text-2xl font-semibold text-white">Study history</h1>
    <p class="mt-1 text-sm text-slate-400">
      Past sessions: typed answers (match score) vs self-grade (memory ratings — separate summary).
    </p>

    <div v-if="deckFilter" class="mt-4 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-sm text-slate-400">
      Filtered to deck
      <NuxtLink :to="`/deck/${deckFilter}`" class="ml-1 font-medium text-emerald-400 hover:underline">open deck</NuxtLink>
      ·
      <NuxtLink to="/learning/history" class="text-slate-500 hover:text-slate-300">clear filter</NuxtLink>
    </div>

    <p v-if="error" class="mt-4 text-sm text-red-400">{{ error }}</p>
    <div v-else-if="pending" class="mt-8 text-center text-slate-500">Loading…</div>
    <div v-else-if="!rows.length" class="mt-8 text-center text-slate-500">No sessions yet.</div>
    <ul v-else class="mt-6 space-y-2">
      <li
        v-for="s in rows"
        :key="s.session_id"
        class="rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3 text-sm"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="font-medium text-slate-100">
              <NuxtLink v-if="s.deck_id" :to="`/deck/${s.deck_id}`" class="hover:text-emerald-400 hover:underline">
                {{ s.deck_title || 'Deck' }}
              </NuxtLink>
              <span v-else class="text-slate-500">—</span>
            </p>
            <p class="mt-1 text-xs text-slate-500">
              {{ s.started_at || '—' }}
              <span v-if="s.ended_at"> → {{ s.ended_at }}</span>
            </p>
          </div>
          <div class="shrink-0 text-right text-xs text-slate-400">
            <span
              class="inline-block rounded border border-slate-700 px-2 py-0.5 capitalize"
            >{{ (s.interaction_mode || 'typed').replaceAll('_', ' ') }}</span>
            <p v-if="s.summary" class="mt-1 text-slate-500">
              <template
                v-if="s.interaction_mode === 'self_grade' && s.summary.self_grade && s.summary.self_grade.cards != null"
              >
                {{ s.summary.self_grade.cards }} cards (last each) · Know {{ s.summary.self_grade.known }} · Unsure
                {{ s.summary.self_grade.unsure }} · Forgot {{ s.summary.self_grade.forgot }}
              </template>
              <template v-else-if="s.interaction_mode === 'self_grade'">
                {{ s.summary.questions ?? 0 }} ratings (self-grade)
              </template>
              <template v-else>
                {{ s.summary.correct ?? 0 }} / {{ s.summary.questions ?? 0 }} correct
              </template>
            </p>
          </div>
        </div>
      </li>
    </ul>

    <div v-if="total > pageSize" class="mt-6 flex justify-center gap-2 text-sm">
      <button
        type="button"
        class="rounded border border-slate-700 px-3 py-1 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
        :disabled="page <= 1 || pending"
        @click="page--; load()"
      >
        Previous
      </button>
      <span class="px-2 py-1 text-slate-500">Page {{ page }}</span>
      <button
        type="button"
        class="rounded border border-slate-700 px-3 py-1 text-slate-300 hover:bg-slate-800 disabled:opacity-40"
        :disabled="page * pageSize >= total || pending"
        @click="page++; load()"
      >
        Next
      </button>
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

type Row = {
  session_id: string
  deck_id?: string
  deck_title?: string
  started_at?: string | null
  ended_at?: string | null
  interaction_mode?: string
  summary?: {
    questions?: number
    correct?: number
    accuracy?: number
    self_grade?: {
      cards?: number
      attempts?: number
      known: number
      unsure: number
      forgot: number
    }
  }
}

const deckFilter = computed(() => (route.query.deck_id as string) || '')
const rows = ref<Row[]>([])
const total = ref(0)
const pageSize = 30
const page = ref(1)
const pending = ref(true)
const error = ref('')

async function load() {
  pending.value = true
  error.value = ''
  try {
    const q = new URLSearchParams()
    q.set('page', String(page.value))
    q.set('page_size', String(pageSize))
    if (deckFilter.value) q.set('deck_id', deckFilter.value)
    const data = await api<{ sessions: Row[]; total: number }>(`/learning/history?${q.toString()}`)
    rows.value = data.sessions || []
    total.value = data.total ?? 0
  } catch (e: unknown) {
    rows.value = []
    total.value = 0
    const fe = e as { data?: { detail?: string } }
    error.value = typeof fe.data?.detail === 'string' ? fe.data.detail : 'Could not load history'
  } finally {
    pending.value = false
  }
}

watch(
  () => route.query.deck_id,
  () => {
    page.value = 1
    void load()
  },
)

onMounted(() => {
  void load()
})
</script>
