<template>
  <div>
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h2 class="text-2xl font-semibold text-white">Storage</h2>
        <p class="mt-2 text-sm text-slate-400">
          Upload any file and save free-form notes. Both are stored together on the server.
        </p>
      </div>
      <button
        type="button"
        class="inline-flex shrink-0 items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
        @click="startNew"
      >
        <Plus class="h-4 w-4" />
        New item
      </button>
    </div>

    <p v-if="listError" class="mt-4 text-sm text-red-400">{{ listError }}</p>

    <div class="mt-8 grid gap-8 lg:grid-cols-[14rem_1fr]">
      <aside class="min-w-0">
        <h3 class="mb-2 text-sm font-medium text-slate-400">Saved</h3>
        <ul v-if="items.length" class="space-y-1">
          <li v-for="item in items" :key="item._id">
            <button
              type="button"
              class="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-800"
              :class="
                selectedId === item._id
                  ? 'bg-slate-800 text-emerald-400'
                  : 'text-slate-300'
              "
              @click="selectItem(item._id)"
            >
              <span class="block truncate font-medium">{{ item.title || 'Untitled' }}</span>
              <span class="block truncate text-xs text-slate-500">
                {{ item.has_file ? item.filename || 'file' : 'text only' }}
              </span>
            </button>
          </li>
        </ul>
        <p v-else class="text-sm text-slate-500">No items yet.</p>
      </aside>

      <section class="min-w-0 rounded-xl border border-slate-800 bg-slate-900/40 p-4 sm:p-5">
        <label class="mb-1 block text-sm font-medium text-slate-300">Title</label>
        <input
          v-model="formTitle"
          class="w-full max-w-xl rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          placeholder="Optional title"
        />

        <label class="mb-1 mt-4 block text-sm font-medium text-slate-300">File</label>
        <input
          ref="fileInputRef"
          type="file"
          class="block w-full max-w-xl text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:py-1.5 file:text-sm file:text-slate-200 hover:file:bg-slate-700"
          @change="onFileChange"
        />
        <p v-if="existingFileLabel" class="mt-2 text-xs text-slate-500">
          Current:
          <button
            type="button"
            class="text-emerald-400 hover:underline"
            :disabled="downloading"
            @click="downloadFile"
          >
            {{ existingFileLabel }}
          </button>
          <button
            type="button"
            class="ml-2 text-red-300/90 hover:underline"
            @click="clearExistingFile"
          >
            Remove
          </button>
        </p>
        <p v-if="pendingFile" class="mt-1 text-xs text-amber-200/80">
          New file selected: {{ pendingFile.name }} ({{ formatBytes(pendingFile.size) }})
        </p>
        <p class="mt-1 text-xs text-slate-500">Max file size 12 MB (MongoDB document limit).</p>

        <label class="mb-1 mt-4 block text-sm font-medium text-slate-300">Contents</label>
        <textarea
          v-model="formContents"
          rows="16"
          class="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-sm text-slate-100 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          placeholder="Write anything…"
        />

        <p v-if="saveError" class="mt-3 text-sm text-red-400">{{ saveError }}</p>
        <p v-if="saveOk" class="mt-3 text-sm text-emerald-400">Saved.</p>

        <div class="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? 'Saving…' : 'Save' }}
          </button>
          <button
            v-if="selectedId"
            type="button"
            class="rounded-lg border border-red-900/60 px-4 py-2 text-sm text-red-300 hover:bg-red-950/40 disabled:opacity-50"
            :disabled="saving"
            @click="remove"
          >
            Delete
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus } from 'lucide-vue-next'

definePageMeta({
  layout: 'default',
  middleware: 'auth',
})

type StorageListItem = {
  _id: string
  title: string
  filename?: string | null
  content_type?: string | null
  file_size?: number
  has_file?: boolean
  updated_at?: string
}

type StorageItem = StorageListItem & {
  contents: string
}

const { api } = useApi()
const config = useRuntimeConfig()
const auth = useAuthStore()

const items = ref<StorageListItem[]>([])
const selectedId = ref<string | null>(null)
const formTitle = ref('')
const formContents = ref('')
const pendingFile = ref<File | null>(null)
const clearFileFlag = ref(false)
const existingHasFile = ref(false)
const existingFilename = ref<string | null>(null)
const existingFileSize = ref(0)
const fileInputRef = ref<HTMLInputElement | null>(null)

const listError = ref('')
const saveError = ref('')
const saveOk = ref(false)
const saving = ref(false)
const downloading = ref(false)

const existingFileLabel = computed(() => {
  if (!existingHasFile.value || clearFileFlag.value) return ''
  const name = existingFilename.value || 'file'
  const size = existingFileSize.value ? ` (${formatBytes(existingFileSize.value)})` : ''
  return `${name}${size}`
})

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function errDetail(err: unknown): string {
  const e = err as { data?: { detail?: string }; message?: string }
  if (typeof e?.data?.detail === 'string') return e.data.detail
  if (typeof e?.message === 'string') return e.message
  return 'Request failed'
}

function resetEditor() {
  selectedId.value = null
  formTitle.value = ''
  formContents.value = ''
  pendingFile.value = null
  clearFileFlag.value = false
  existingHasFile.value = false
  existingFilename.value = null
  existingFileSize.value = 0
  saveError.value = ''
  saveOk.value = false
  if (fileInputRef.value) fileInputRef.value.value = ''
}

function startNew() {
  resetEditor()
}

function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const f = input.files?.[0] ?? null
  pendingFile.value = f
  if (f) clearFileFlag.value = false
}

function clearExistingFile() {
  clearFileFlag.value = true
  pendingFile.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function loadList() {
  listError.value = ''
  try {
    const data = await api<{ items: StorageListItem[] }>('/storage')
    items.value = data.items ?? []
  } catch (err) {
    listError.value = errDetail(err)
  }
}

async function selectItem(id: string) {
  saveError.value = ''
  saveOk.value = false
  try {
    const data = await api<StorageItem>(`/storage/${id}`)
    selectedId.value = data._id
    formTitle.value = data.title || ''
    formContents.value = data.contents || ''
    pendingFile.value = null
    clearFileFlag.value = false
    existingHasFile.value = !!data.has_file
    existingFilename.value = data.filename || null
    existingFileSize.value = data.file_size || 0
    if (fileInputRef.value) fileInputRef.value.value = ''
  } catch (err) {
    saveError.value = errDetail(err)
  }
}

async function save() {
  saving.value = true
  saveError.value = ''
  saveOk.value = false
  try {
    const body = new FormData()
    body.append('title', formTitle.value)
    body.append('contents', formContents.value)
    if (pendingFile.value) {
      body.append('file', pendingFile.value)
    }
    if (selectedId.value && clearFileFlag.value && !pendingFile.value) {
      body.append('clear_file', '1')
    }

    let data: StorageItem
    if (selectedId.value) {
      data = await api<StorageItem>(`/storage/${selectedId.value}`, {
        method: 'PUT',
        body,
      })
    } else {
      data = await api<StorageItem>('/storage', {
        method: 'POST',
        body,
      })
    }
    selectedId.value = data._id
    formTitle.value = data.title || ''
    formContents.value = data.contents || ''
    pendingFile.value = null
    clearFileFlag.value = false
    existingHasFile.value = !!data.has_file
    existingFilename.value = data.filename || null
    existingFileSize.value = data.file_size || 0
    if (fileInputRef.value) fileInputRef.value.value = ''
    saveOk.value = true
    await loadList()
  } catch (err) {
    saveError.value = errDetail(err)
  } finally {
    saving.value = false
  }
}

async function remove() {
  if (!selectedId.value) return
  if (!confirm('Delete this item and its file?')) return
  saving.value = true
  saveError.value = ''
  try {
    await api(`/storage/${selectedId.value}`, { method: 'DELETE' })
    resetEditor()
    await loadList()
  } catch (err) {
    saveError.value = errDetail(err)
  } finally {
    saving.value = false
  }
}

async function downloadFile() {
  if (!selectedId.value || !existingHasFile.value) return
  downloading.value = true
  saveError.value = ''
  try {
    const base = (config.public.apiBase as string).replace(/\/$/, '')
    const res = await fetch(`${base}/storage/${selectedId.value}/file`, {
      headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
    })
    if (!res.ok) {
      let detail = `Download failed (${res.status})`
      try {
        const j = await res.json()
        if (j?.detail) detail = String(j.detail)
      } catch {
        /* ignore */
      }
      throw new Error(detail)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = existingFilename.value || 'download'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (err) {
    saveError.value = errDetail(err)
  } finally {
    downloading.value = false
  }
}

onMounted(() => {
  loadList()
})
</script>
