<template>
  <Sheet :open="uiStore.sidebarOpen && isMobile" @update:open="(v) => !v && uiStore.closeSidebar()">
    <SheetContent side="left" class="p-0 w-64 bg-sidebar">
      <AppSidebar />
    </SheetContent>
  </Sheet>
</template>

<script setup lang="ts">
import { useMediaQuery } from '@vueuse/core'
import { Sheet, SheetContent } from '@/platform/components/ui/sheet'
import AppSidebar from './AppSidebar.vue'
import { useUiStore } from '@/platform/stores/ui'

const uiStore = useUiStore()
const isMobile = useMediaQuery('(max-width: 1023px)')
</script>
