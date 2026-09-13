<template>
  <div :class="styles.root">
    <p class="text-sm" :class="styles.text">
      <slot />
    </p>
    <slot name="cta" :text-class="styles.text" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ variant: 'info' | 'warning' | 'danger' | 'success' }>()

const styles = computed(() => {
  if (props.variant === 'danger')
    return {
      root: 'border-b border-destructive/20 bg-destructive/10 px-4 py-2.5 flex items-center justify-between gap-4',
      text: 'text-destructive',
    }
  if (props.variant === 'warning')
    return {
      root: 'border-b border-warning/20 bg-warning/10 px-4 py-2.5 flex items-center justify-between gap-4',
      text: 'text-warning',
    }
  if (props.variant === 'success')
    return {
      root: 'border-b border-success/20 bg-success/10 px-4 py-2.5 flex items-center justify-between gap-4',
      text: 'text-success',
    }
  return {
    root: 'border-b border-info/20 bg-info/10 px-4 py-2.5 flex items-center justify-between gap-4',
    text: 'text-info',
  }
})
</script>
