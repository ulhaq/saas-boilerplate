<template>
  <WaitlistPage v-if="showWaitlist" />
  <component :is="currentLayout" v-else>
    <RouterView />
  </component>
  <Toaster />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { defineAsyncComponent } from 'vue'
import { useHead } from '@unhead/vue'
import { Toaster } from '@/platform/components/ui/toast'
import { useAuthStore } from '@/platform/stores/auth'
import { buildRouteHead } from '@/router/seo'
// Statically imported: this is the layout wrapping every prerendered marketing
// page, and an async component would resolve to an empty placeholder in the
// build output. The app-only layouts stay lazy.
import LandingLayout from '@/platform/layouts/LandingLayout.vue'

const AuthLayout = defineAsyncComponent(() => import('@/platform/layouts/AuthLayout.vue'))
const DashboardLayout = defineAsyncComponent(() => import('@/platform/layouts/DashboardLayout.vue'))
const WaitlistPage = defineAsyncComponent(() => import('@/platform/components/WaitlistPage.vue'))

const route = useRoute()
const authStore = useAuthStore()

// Per-page title, description, canonical, robots and OG/Twitter tags. Runs
// during the prerender build so the emitted HTML carries them, and re-runs on
// every client-side navigation and language switch.
useHead(computed(() => buildRouteHead(route.path, route.meta.breadcrumb)))

// When waitlist mode is on, the public landing route ('/') is replaced by a
// standalone waitlist page. All other routes (login, register, app) are
// untouched.
const waitlistMode = import.meta.env.VITE_WAITLIST_MODE === 'true'
const showWaitlist = computed(() => waitlistMode && route.path === '/')

const currentLayout = computed(() => {
  const layout = route.meta.layout ?? 'auth'
  if (layout === 'auto') return authStore.isAuthenticated ? DashboardLayout : AuthLayout
  if (layout === 'landing') return LandingLayout
  return layout === 'dashboard' ? DashboardLayout : AuthLayout
})
</script>
