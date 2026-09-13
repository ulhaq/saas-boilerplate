<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/platform/lib/utils'

// `as` lets a caller place the title at the right heading rank for its page -
// an auth card sits directly under the layout's <h1>, so it needs an <h2>.
// Defaults to h3, which is what every existing call site already renders.
const props = withDefaults(
  defineProps<{
    class?: HTMLAttributes['class']
    as?: 'h1' | 'h2' | 'h3' | 'h4'
  }>(),
  { as: 'h3' },
)
</script>

<template>
  <component :is="props.as" :class="cn('font-semibold leading-none tracking-tight', props.class)">
    <slot />
  </component>
</template>
