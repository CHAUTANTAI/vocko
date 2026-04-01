<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="presentation"
    >
      <div
        class="absolute inset-0 bg-black/60 backdrop-blur-[1px]"
        aria-hidden="true"
        @click="onBackdrop"
      />
      <div
        class="relative w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-6 shadow-xl"
        role="alertdialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        :aria-describedby="descId"
        @keydown.escape.prevent="onCancel"
      >
        <h3 :id="titleId" class="text-lg font-semibold text-white">
          {{ title }}
        </h3>
        <p :id="descId" class="mt-2 text-sm leading-relaxed text-slate-300">
          {{ message }}
        </p>
        <div class="mt-6 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            class="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800"
            @click="onCancel"
          >
            {{ cancelLabel }}
          </button>
          <button
            type="button"
            class="rounded-lg px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            :class="danger ? 'bg-red-600 hover:bg-red-500' : 'bg-emerald-600 hover:bg-emerald-500'"
            @click="onConfirm"
          >
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useId } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title: string
    message: string
    confirmLabel?: string
    cancelLabel?: string
    /** Red confirm button (destructive actions). */
    danger?: boolean
    /** Close when clicking the backdrop (default true). */
    closeOnBackdrop?: boolean
  }>(),
  {
    confirmLabel: 'Confirm',
    cancelLabel: 'Cancel',
    danger: true,
    closeOnBackdrop: true,
  },
)

const emit = defineEmits<{
  'update:modelValue': [boolean]
  confirm: []
  cancel: []
}>()

const titleId = useId()
const descId = useId()

function onCancel() {
  emit('cancel')
  emit('update:modelValue', false)
}

function onConfirm() {
  emit('confirm')
  emit('update:modelValue', false)
}

function onBackdrop() {
  if (props.closeOnBackdrop) {
    onCancel()
  }
}
</script>
