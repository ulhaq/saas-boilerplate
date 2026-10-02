import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createHead } from '@unhead/vue/client'
import App from './App.vue'
import { createAppRouter } from './router'
import { i18n } from './plugins/i18n'
import { configureApp } from '@/platform/config'
import { initTelemetry } from '@/platform/lib/telemetry'
import { products } from '@/products'
import '@/platform/notifications/billing'
import './assets/index.css'

for (const product of products) product.setup?.()
const homeRoute = products.find((product) => product.homeRoute)?.homeRoute
if (homeRoute) configureApp({ homeRoute })

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(createHead())
app.use(createAppRouter())
void initTelemetry(app)
app.mount('#app')
