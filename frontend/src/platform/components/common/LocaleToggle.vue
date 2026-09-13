<template>
  <Button
    variant="ghost"
    class="px-2"
    :class="
      variant === 'slate'
        ? 'text-slate-700 hover:text-slate-900 hover:bg-slate-100'
        : 'text-muted-foreground hover:text-foreground'
    "
    :aria-label="`Switch language (current: ${locale.toUpperCase()})`"
    @click="cycle"
  >
    {{ locale.toUpperCase() }}
  </Button>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Button } from '@/platform/components/ui/button'
import { LOCALE_ORDER } from '@/plugins/i18n'
import type { SupportedLocale } from '@/plugins/i18n'
import { useLocalePath } from '@/platform/composables/useLocalePath'
import type { Locale } from '@/router/public-routes'

const props = defineProps<{
  variant?: 'default' | 'slate'
  onSwitch?: (lang: SupportedLocale) => void | Promise<void>
}>()

const { locale } = useI18n()
const { setLocale } = useLocalePath()

async function cycle() {
  const current = LOCALE_ORDER.indexOf(locale.value as SupportedLocale)
  const next = LOCALE_ORDER[(current + 1) % LOCALE_ORDER.length]

  // On a marketing page this also navigates to that page's URL in the new
  // language (`/da/priser` -> `/en/pricing`), so the URL never disagrees with
  // what's on screen. Elsewhere it just switches the language.
  await setLocale(next as Locale)
  props.onSwitch?.(next)
}
</script>
