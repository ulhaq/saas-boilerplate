<template>
  <div
    role="radiogroup"
    :aria-label="$t('subscription.currency')"
    class="inline-flex items-center gap-1 rounded-md border p-0.5"
  >
    <button
      v-for="option in currencies"
      :key="option"
      type="button"
      role="radio"
      :aria-checked="option === modelValue"
      :class="
        cn(
          'rounded px-2.5 py-1 text-xs font-medium transition-colors',
          option === modelValue
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground',
        )
      "
      @click="emit('update:modelValue', option)"
    >
      {{ option.toUpperCase() }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/foundation/lib/utils'

/** Picks the currency the plans are shown and bought in. */
defineProps<{ currencies: string[]; modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', currency: string): void }>()
</script>
