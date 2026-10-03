<template>
  <TooltipProvider :delay-duration="300">
    <div class="h-screen bg-background flex overflow-hidden">
      <!-- Desktop Sidebar -->
      <aside
        class="hidden lg:flex flex-col w-64 shrink-0 border-r border-sidebar-border bg-sidebar shadow-md transition-all duration-200"
      >
        <AppSidebar />
      </aside>

      <!-- Main content -->
      <div class="flex-1 flex flex-col min-w-0">
        <AppTopbar />
        <component :is="banner" v-for="(banner, i) in banners" :key="i" />
        <main class="flex-1 p-6 overflow-auto">
          <slot />
        </main>
      </div>

      <!-- Mobile sidebar -->
      <MobileSidebar />

      <!-- Global confirm dialog -->
      <ConfirmDialog />
    </div>
  </TooltipProvider>
</template>

<script setup lang="ts">
import AppSidebar from '@/foundation/components/layout/AppSidebar.vue'
import AppTopbar from '@/foundation/components/layout/AppTopbar.vue'
import MobileSidebar from '@/foundation/components/layout/MobileSidebar.vue'
import ConfirmDialog from '@/foundation/components/common/ConfirmDialog.vue'
import { TooltipProvider } from '@/foundation/components/ui/tooltip'
import { useTawkChat } from '@/foundation/composables/useTawkChat'
import { registeredBanners } from '@/foundation/banners'

const banners = registeredBanners()

useTawkChat()
</script>
