<template>
  <Sheet :open="uiStore.sidebarOpen && isMobile" @update:open="(v) => !v && uiStore.closeSidebar()">
    <SheetContent side="left" class="p-0 w-64 bg-sidebar">
      <AppSidebar />
    </SheetContent>
  </Sheet>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMediaQuery } from '@vueuse/core'
import { Sheet, SheetContent } from '@/foundation/components/ui/sheet'
import AppSidebar from './AppSidebar.vue'
import { useUiStore } from '@/foundation/stores/ui'

const uiStore = useUiStore()
const route = useRoute()
const isMobile = useMediaQuery('(max-width: 1023px)')

// Close the drawer once a menu item has navigated somewhere.
watch(
  () => route.fullPath,
  () => uiStore.closeSidebar(),
)
</script>
