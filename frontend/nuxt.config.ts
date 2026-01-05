export default defineNuxtConfig({
  ssr: false, // 禁用 SSR，避免重复请求
  devtools: { enabled: true },
  modules: ['@element-plus/nuxt'],
  css: ['element-plus/dist/index.css'],
  build: {
    transpile: ['element-plus']
  },
  runtimeConfig: {
    public: {
      apiBase: 'http://127.0.0.1:8000'
    }
  },
  compatibilityDate: '2024-01-01'
})
