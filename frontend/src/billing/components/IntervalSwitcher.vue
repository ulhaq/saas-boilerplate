<template>
  <div
    role="radiogroup"
    :aria-label="$t('subscription.billingInterval')"
    class="inline-flex items-center gap-1 rounded-md border p-0.5"
  >
    <button
      v-for="option in intervals"
      :key="option"
      type="button"
      role="radio"
      :aria-checked="option === modelValue"
      :class="
        cn(
          'inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors',
          option === modelValue
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground',
        )
      "
      @click="emit('update:modelValue', option)"
    >
      {{
        te(`subscription.intervalOptions.${option}`)
          ? t(`subscription.intervalOptions.${option}`)
          : option
      }}
      <span
        v-if="option === 'year' && yearlySaving"
        :class="
          cn(
            'rounded-full px-1.5 py-px text-[10px] font-semibold',
            option === modelValue ? 'bg-primary-foreground/20' : 'bg-success/10 text-success',
          )
        "
        >{{ yearlySaving }}</span
      >
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { cn } from '@/foundation/lib/utils'

/** Picks whether the plans are shown and bought monthly or yearly. `yearlySaving`: what
 * paying yearly saves, as the badge on the Yearly option ("2 months free"; none: no badge). */
defineProps<{ intervals: string[]; modelValue: string; yearlySaving?: string | null }>()
const emit = defineEmits<{ (e: 'update:modelValue', interval: string): void }>()

const { t, te } = useI18n()
</script>
