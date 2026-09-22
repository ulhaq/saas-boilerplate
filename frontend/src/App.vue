<template>
  <component :is="currentLayout">
    <RouterView />
  </component>
  <Toaster />
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useHead } from '@unhead/vue'
import { Toaster } from '@/platform/components/ui/toast'
import { useAuthStore } from '@/platform/stores/auth'
import { buildRouteHead } from '@/router/seo'

const AuthLayout = defineAsyncComponent(() => import('@/platform/layouts/AuthLayout.vue'))
const DashboardLayout = defineAsyncComponent(() => import('@/platform/layouts/DashboardLayout.vue'))

const route = useRoute()
const authStore = useAuthStore()

// Per-page title, description, canonical, robots and OG/Twitter tags; re-runs
// on every navigation and language switch.
useHead(computed(() => buildRouteHead(route.path, route.meta.breadcrumb)))

const currentLayout = computed(() => {
  const layout = route.meta.layout ?? 'auth'
  if (layout === 'auto') return authStore.isAuthenticated ? DashboardLayout : AuthLayout
  return layout === 'dashboard' ? DashboardLayout : AuthLayout
})
</script>
