<template>
  <Transition
    enter-active-class="transition-transform duration-300 ease-out"
    enter-from-class="translate-y-full"
    enter-to-class="translate-y-0"
    leave-active-class="transition-transform duration-200 ease-in"
    leave-from-class="translate-y-0"
    leave-to-class="translate-y-full"
  >
    <!--
      A landmark, not a plain div: the banner sits outside <main>, so without
      one its text is content that belongs to no region - which is what breaks
      the accessibility tree for screen readers and agents alike.
    -->
    <aside
      v-if="visible"
      :aria-label="$t('cookie.title')"
      class="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-background px-4 py-4 shadow-lg sm:px-6"
    >
      <div
        class="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
      >
        <div>
          <p class="text-sm font-medium text-foreground">{{ $t('cookie.title') }}</p>
          <p class="mt-0.5 text-sm text-muted-foreground">
            {{ $t('cookie.description') }}
            <RouterLink :to="localePath('privacy')" class="underline hover:text-foreground">
              {{ $t('cookie.learnMore') }}
            </RouterLink>
          </p>
        </div>
        <div class="flex shrink-0 gap-2">
          <button
            class="rounded-md border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-muted focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            @click="declineOptional"
          >
            {{ $t('cookie.necessaryOnly') }}
          </button>
          <button
            class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            @click="acceptAll"
          >
            {{ $t('cookie.acceptAll') }}
          </button>
        </div>
      </div>
    </aside>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useCookieConsent } from '@/platform/composables/useCookieConsent'
import { useLocalePath } from '@/platform/composables/useLocalePath'

const { localePath } = useLocalePath()

const { hasDecided, settingsOpen, acceptAll, declineOptional } = useCookieConsent()

const visible = computed(() => !hasDecided.value || settingsOpen.value)
</script>
