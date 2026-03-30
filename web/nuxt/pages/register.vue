<template>
  <div class="mx-auto max-w-md">
    <h2 class="text-2xl font-semibold text-white">Create account</h2>
    <p class="mt-1 text-sm text-slate-400">Start building your vocabulary decks.</p>

    <Form
      class="mt-8 space-y-4"
      :validation-schema="schema"
      @submit="onSubmit"
    >
      <div>
        <label for="email" class="mb-1 block text-sm font-medium text-slate-300">Email</label>
        <Field id="email" name="email" v-slot="{ field, errors }">
          <input
            v-bind="field"
            type="email"
            autocomplete="email"
            class="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <p v-if="errors[0]" class="mt-1 text-sm text-red-400">{{ errors[0] }}</p>
        </Field>
      </div>
      <div>
        <label for="displayName" class="mb-1 block text-sm font-medium text-slate-300"
          >Display name</label
        >
        <Field id="displayName" name="displayName" v-slot="{ field, errors }">
          <input
            v-bind="field"
            type="text"
            autocomplete="nickname"
            class="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <p v-if="errors[0]" class="mt-1 text-sm text-red-400">{{ errors[0] }}</p>
        </Field>
      </div>
      <div>
        <label for="password" class="mb-1 block text-sm font-medium text-slate-300">Password</label>
        <Field id="password" name="password" v-slot="{ field, errors }">
          <input
            v-bind="field"
            type="password"
            autocomplete="new-password"
            class="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <p v-if="errors[0]" class="mt-1 text-sm text-red-400">{{ errors[0] }}</p>
        </Field>
      </div>
      <p v-if="formError" class="text-sm text-red-400">{{ formError }}</p>
      <button
        type="submit"
        class="w-full rounded-lg bg-emerald-600 py-2.5 font-medium text-white hover:bg-emerald-500"
      >
        Register
      </button>
    </Form>

    <p class="mt-6 text-center text-sm text-slate-400">
      Already have an account?
      <NuxtLink to="/login" class="text-emerald-400 hover:underline">Log in</NuxtLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { Form, Field } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/yup'
import * as yup from 'yup'

definePageMeta({
  layout: 'default',
  middleware: 'guest',
})

const schema = toTypedSchema(
  yup.object({
    email: yup.string().email('Valid email required').required('Email is required'),
    displayName: yup.string().min(1, 'Name is required').required('Display name is required'),
    password: yup.string().min(6, 'At least 6 characters').required('Password is required'),
  }),
)

const router = useRouter()
const { register } = useAuth()
const formError = ref('')

async function onSubmit(values: { email: string; displayName: string; password: string }) {
  formError.value = ''
  try {
    await register(values.email, values.password, values.displayName)
    await router.push('/deck')
  } catch {
    formError.value = 'Registration failed (email may already be in use)'
  }
}
</script>
