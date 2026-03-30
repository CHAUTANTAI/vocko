<template>
  <div class="mx-auto max-w-md">
    <h2 class="text-2xl font-semibold text-white">Log in</h2>
    <p class="mt-1 text-sm text-slate-400">Welcome back to VocKO.</p>

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
            class="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="you@example.com"
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
            autocomplete="current-password"
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
        Log in
      </button>
    </Form>

    <p class="mt-6 text-center text-sm text-slate-400">
      No account?
      <NuxtLink to="/register" class="text-emerald-400 hover:underline">Register</NuxtLink>
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
    password: yup.string().min(6, 'At least 6 characters').required('Password is required'),
  }),
)

const router = useRouter()
const { login } = useAuth()
const formError = ref('')

async function onSubmit(values: { email: string; password: string }) {
  formError.value = ''
  try {
    await login(values.email, values.password)
    await router.push('/deck')
  } catch {
    formError.value = 'Invalid credentials'
  }
}
</script>
