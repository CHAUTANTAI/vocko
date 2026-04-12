<template>
  <ClientOnly>
    <div
      class="overflow-hidden rounded-lg border border-slate-700 bg-slate-950 focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500"
    >
      <div
        v-if="editor"
        class="flex flex-wrap gap-1 border-b border-slate-800 bg-slate-900/80 px-2 py-1.5"
      >
        <button
          type="button"
          class="rounded px-2 py-1 text-xs font-semibold text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-40"
          :disabled="disabled"
          :class="{ 'bg-slate-800 text-emerald-300': editor.isActive('bold') }"
          @click="editor.chain().focus().toggleBold().run()"
        >
          B
        </button>
        <button
          type="button"
          class="rounded px-2 py-1 text-xs italic text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-40"
          :disabled="disabled"
          :class="{ 'bg-slate-800 text-emerald-300': editor.isActive('italic') }"
          @click="editor.chain().focus().toggleItalic().run()"
        >
          I
        </button>
        <button
          type="button"
          class="rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-40"
          :disabled="disabled"
          :class="{ 'bg-slate-800 text-emerald-300': editor.isActive('bulletList') }"
          @click="editor.chain().focus().toggleBulletList().run()"
        >
          • List
        </button>
        <button
          type="button"
          class="rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-40"
          :disabled="disabled"
          :class="{ 'bg-slate-800 text-emerald-300': editor.isActive('orderedList') }"
          @click="editor.chain().focus().toggleOrderedList().run()"
        >
          1. List
        </button>
      </div>
      <editor-content v-if="editor" :editor="editor" class="rich-editor-content" />
    </div>
    <template #fallback>
      <div
        class="min-h-[8.5rem] rounded-lg border border-slate-700 bg-slate-950"
        aria-hidden="true"
      />
    </template>
  </ClientOnly>
</template>

<script setup lang="ts">
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { watch } from 'vue'
import { isEmptyRichText } from '~/utils/richText'

const props = withDefaults(
  defineProps<{
    modelValue: string
    disabled?: boolean
  }>(),
  { disabled: false, modelValue: '' },
)

const emit = defineEmits<{
  'update:modelValue': [string]
  blur: []
}>()

const editor = useEditor({
  extensions: [StarterKit],
  content: props.modelValue || '<p></p>',
  immediatelyRender: false,
  editable: !props.disabled,
  editorProps: {
    attributes: {
      class:
        'prose prose-invert prose-sm max-w-none min-h-[6rem] px-3 py-2 text-slate-100 focus:outline-none [&_li]:my-0.5 [&_ol]:my-1 [&_p]:my-1 [&_ul]:my-1',
    },
  },
  onUpdate: ({ editor: ed }) => {
    emit('update:modelValue', ed.getHTML())
  },
  onBlur: () => {
    emit('blur')
  },
})

watch(
  () => props.modelValue,
  (html) => {
    const ed = editor.value
    if (!ed || ed.isDestroyed) return
    const incoming = html ?? ''
    const current = ed.getHTML()
    if (incoming === current) return
    if (!incoming.trim() && isEmptyRichText(current)) return
    ed.commands.setContent(incoming || '<p></p>', false)
  },
)

watch(
  () => props.disabled,
  (d) => {
    editor.value?.setEditable(!d)
  },
)
</script>

<style scoped>
:deep(.rich-editor-content .ProseMirror) {
  outline: none;
}
</style>
