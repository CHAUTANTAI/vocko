<template>
  <div>
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-white">Tin nổi bật</h2>
        <p class="mt-2 text-sm text-slate-400">
          Tóm tắt tiếng Việt từ RSS VnExpress (Thời sự & Thế giới). Nguồn gốc mỗi bài nằm ở liên kết tiêu đề.
        </p>
        <p v-if="digest" class="mt-1 text-xs text-slate-500">
          Ngày {{ digest.date }}
          <span v-if="builtLabel"> · Cập nhật {{ builtLabel }}</span>
        </p>
      </div>
      <button
        type="button"
        class="inline-flex shrink-0 items-center gap-2 rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="loading || refreshing"
        @click="refresh"
      >
        <RefreshCw class="h-4 w-4" :class="{ 'animate-spin': refreshing }" />
        Cập nhật lại
      </button>
    </div>

    <p v-if="loadError" class="mt-4 text-sm text-red-400">{{ loadError }}</p>
    <p v-if="loading && !digest" class="mt-8 text-sm text-slate-400">
      Đang tải / tạo bản tin trong ngày (lần đầu có thể mất khoảng một phút)…
    </p>

    <template v-if="digest">
      <section class="mt-8">
        <h3 class="text-lg font-medium text-emerald-400">Trong nước</h3>
        <ul class="mt-3 space-y-3">
          <li
            v-for="(item, i) in digest.domestic"
            :key="`d-${i}-${item.url}`"
            class="rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
          >
            <a
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              class="font-medium text-white hover:text-emerald-400 hover:underline"
            >
              {{ item.title }}
            </a>
            <p class="mt-2 text-sm leading-relaxed text-slate-300">{{ item.summary }}</p>
            <p class="mt-2 text-xs text-slate-500">Nguồn: VnExpress</p>
          </li>
        </ul>
        <p v-if="!digest.domestic.length" class="mt-3 text-sm text-slate-500">Chưa có tin.</p>
      </section>

      <section class="mt-10">
        <h3 class="text-lg font-medium text-emerald-400">Thế giới</h3>
        <ul class="mt-3 space-y-3">
          <li
            v-for="(item, i) in digest.world"
            :key="`w-${i}-${item.url}`"
            class="rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
          >
            <a
              :href="item.url"
              target="_blank"
              rel="noopener noreferrer"
              class="font-medium text-white hover:text-emerald-400 hover:underline"
            >
              {{ item.title }}
            </a>
            <p class="mt-2 text-sm leading-relaxed text-slate-300">{{ item.summary }}</p>
            <p class="mt-2 text-xs text-slate-500">Nguồn: VnExpress</p>
          </li>
        </ul>
        <p v-if="!digest.world.length" class="mt-3 text-sm text-slate-500">Chưa có tin.</p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

type NewsItem = {
  title: string
  url: string
  summary: string
  published_at?: string
}

type NewsDigest = {
  date: string
  built_at?: string
  source?: string
  domestic: NewsItem[]
  world: NewsItem[]
}

const { api } = useApi()
const digest = ref<NewsDigest | null>(null)
const loading = ref(false)
const refreshing = ref(false)
const loadError = ref('')

const NEWS_TIMEOUT_MS = 180_000

const builtLabel = computed(() => {
  const raw = digest.value?.built_at
  if (!raw) return ''
  try {
    return new Date(raw).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' })
  } catch {
    return raw
  }
})

function errMessage(err: unknown): string {
  const e = err as { data?: { detail?: string }; statusMessage?: string; message?: string }
  const detail = e?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (typeof e?.statusMessage === 'string' && e.statusMessage) return e.statusMessage
  if (typeof e?.message === 'string' && e.message) return e.message
  return 'Không tải được tin.'
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    digest.value = await api<NewsDigest>('/news/today', { timeout: NEWS_TIMEOUT_MS })
  } catch (err) {
    loadError.value = errMessage(err)
  } finally {
    loading.value = false
  }
}

async function refresh() {
  refreshing.value = true
  loadError.value = ''
  try {
    digest.value = await api<NewsDigest>('/news/refresh', {
      method: 'POST',
      timeout: NEWS_TIMEOUT_MS,
    })
  } catch (err) {
    loadError.value = errMessage(err)
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  load()
})
</script>
