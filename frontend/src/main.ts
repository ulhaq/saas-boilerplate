import { ViteSSG } from 'vite-ssg'
import { createPinia } from 'pinia'
import App from './App.vue'
import { routes, installRouterGuards } from './router'
import { i18n } from './plugins/i18n'
import { configureApp } from '@/platform/config'
import { initTelemetry } from '@/platform/lib/telemetry'
import './assets/index.css'
import '@/example'

configureApp({ homeRoute: '/dashboard' })

// `ViteSSG` owns the app and router so the marketing routes listed in
// `ssgOptions.includedRoutes` (vite.config.ts) can be rendered to static HTML at
// build time. In the browser this behaves exactly like `createApp` + `mount`.
export const createApp = ViteSSG(App, { routes }, ({ app, router, isClient }) => {
  app.use(createPinia())
  app.use(i18n)
  installRouterGuards(router)
  // Browser only: not during the SSG prerender
  if (isClient) void initTelemetry(app)
})
