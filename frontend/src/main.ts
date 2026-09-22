import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createHead } from '@unhead/vue/client'
import App from './App.vue'
import { createAppRouter } from './router'
import { i18n } from './plugins/i18n'
import { configureApp } from '@/platform/config'
import { initTelemetry } from '@/platform/lib/telemetry'
import './assets/index.css'
import '@/example'

configureApp({ homeRoute: '/dashboard' })

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(createHead())
app.use(createAppRouter())
void initTelemetry(app)
app.mount('#app')
