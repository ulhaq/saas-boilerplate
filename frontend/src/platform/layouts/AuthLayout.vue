<template>
  <div
    class="min-h-screen bg-gradient-to-br from-background via-muted/30 to-background flex items-center justify-center p-4"
  >
    <div class="w-full max-w-md animate-fade-in">
      <header class="mb-8 text-center">
        <RouterLink to="/" class="inline-flex flex-col items-center gap-4">
          <div class="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-primary">
            <Radar class="w-5 h-5 text-primary-foreground" />
          </div>
          <h1 class="text-2xl font-semibold tracking-tight text-foreground">
            {{ $t('app.name') }}
          </h1>
        </RouterLink>
      </header>
      <!-- A <main> landmark: without one the card's content belongs to no
           region, which leaves the accessibility tree malformed. -->
      <main>
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { Radar } from 'lucide-vue-next'
useI18n()
</script>
