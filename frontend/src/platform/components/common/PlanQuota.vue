<template>
  <!-- Progress bar + count -->
  <div v-if="variant === 'bar'" class="flex items-center gap-2">
    <div class="w-20 h-1.5 rounded-full bg-muted overflow-hidden">
      <div
        class="h-full rounded-full transition-all"
        :class="barColor"
        :style="{ width: `${pct}%` }"
      />
    </div>
    <span class="text-xs tabular-nums" :class="textColor">{{ label }}</span>
  </div>

  <!-- Colored badge pill -->
  <span
    v-else-if="variant === 'badge'"
    class="inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium tabular-nums transition-colors"
    :class="badgeClass"
  >
    {{ label }}
  </span>

  <!-- Dot + fraction -->
  <span
    v-else
    class="inline-flex items-center gap-1.5 text-xs font-medium tabular-nums"
    :class="textColor"
  >
    <span class="w-1.5 h-1.5 rounded-full shrink-0" :class="dotColor" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  count: number
  limit: number | null
  labelKey?: string
  variant: 'bar' | 'badge' | 'dot'
}>()

const pct = computed(() =>
  props.limit ? Math.min(100, Math.round((props.count / props.limit) * 100)) : 0,
)

const isAtLimit = computed(() => props.limit !== null && props.count >= props.limit)
const isNearLimit = computed(() => props.limit !== null && props.count >= props.limit * 0.8)

const label = computed(() =>
  props.limit !== null ? `${props.count} / ${props.limit}` : `${props.count}`,
)

const textColor = computed(() => {
  if (isAtLimit.value) return 'text-destructive'
  if (isNearLimit.value) return 'text-warning'
  return 'text-muted-foreground'
})

const barColor = computed(() => {
  if (isAtLimit.value) return 'bg-destructive'
  if (isNearLimit.value) return 'bg-warning'
  return 'bg-success'
})

const dotColor = computed(() => {
  if (isAtLimit.value) return 'bg-destructive'
  if (isNearLimit.value) return 'bg-warning'
  return 'bg-success'
})

const badgeClass = computed(() => {
  if (isAtLimit.value) return 'border-destructive/30 bg-destructive/10 text-destructive'
  if (isNearLimit.value) return 'border-warning/30 bg-warning/10 text-warning'
  return 'border-border bg-muted/50 text-muted-foreground'
})
</script>
