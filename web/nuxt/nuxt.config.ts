import typography from '@tailwindcss/typography'

export default defineNuxtConfig({
  devtools: { enabled: true },
  // Vite 7 + import-analysis: cần Environment API để alias `#app-manifest` trên client (nuxt/nuxt#30461).
  experimental: {
    viteEnvironmentApi: true,
  },
  compatibilityDate: '2024-11-01',
  devServer: {
    host: '127.0.0.1',
    port: 3000,
  },
  modules: ['@nuxtjs/tailwindcss', '@pinia/nuxt', '@vee-validate/nuxt'],
  /** Inline Tailwind config avoids Windows ESM loading `tailwind.config.*` via absolute `c:\` paths. */
  tailwindcss: {
    quiet: true,
    config: {
      content: [
        './components/**/*.{vue,js,ts}',
        './layouts/**/*.vue',
        './pages/**/*.vue',
        './plugins/**/*.{js,ts}',
        './app.vue',
      ],
      theme: {
        extend: {
          fontFamily: {
            sans: ['system-ui', 'sans-serif'],
          },
        },
      },
      darkMode: 'class',
      plugins: [typography],
    },
  },
  vite: {
    server: {
      strictPort: true,
    },
  },
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      htmlAttrs: {
        lang: 'en',
        class: 'bg-slate-950',
      },
      meta: [
        {
          name: 'viewport',
          content: 'width=device-width, initial-scale=1, viewport-fit=cover',
        },
        { name: 'theme-color', content: '#020617' },
        { name: 'color-scheme', content: 'dark' },
      ],
    },
  },
  runtimeConfig: {
    public: {
      // Fallback; Nuxt merges `NUXT_PUBLIC_API_BASE` from the environment (no `process.env` needed here).
      apiBase: 'http://localhost:8000',
    },
  },
})
