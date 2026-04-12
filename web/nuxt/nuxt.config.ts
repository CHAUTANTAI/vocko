export default defineNuxtConfig({
  devtools: { enabled: true },
  compatibilityDate: '2024-11-01',
  devServer: {
    host: '127.0.0.1',
    port: 3000,
  },
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt', '@vee-validate/nuxt'],
  vite: {
    server: {
      strictPort: true,
    },
  },
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    public: {
      // Fallback; Nuxt merges `NUXT_PUBLIC_API_BASE` from the environment (no `process.env` needed here).
      apiBase: 'http://localhost:8000',
    },
  },
})
