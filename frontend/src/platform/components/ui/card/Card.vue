<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/platform/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div
    :class="
      cn(
        'rounded-xl border bg-card text-card-foreground shadow-sm transition-shadow duration-200 hover:shadow-md',
        props.class,
      )
    "
  >
    <slot />
  </div>
</template>
