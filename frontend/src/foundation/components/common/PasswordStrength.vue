<template>
  <div v-if="password.length > 0" class="space-y-1">
    <div class="flex gap-1">
      <div
        v-for="i in 4"
        :key="i"
        class="h-1 flex-1 rounded-full transition-colors duration-200"
        :class="i <= bars ? scoreColor : 'bg-muted'"
      />
    </div>
    <p class="text-xs" :class="labelColor">{{ label }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ password: string }>()
const { t } = useI18n()

const score = computed(() => {
  const p = props.password
  let s = 0
  if (p.length >= 8) s++
  if (p.length >= 12) s++
  if (/[0-9]/.test(p)) s++
  if (/[^a-zA-Z0-9]/.test(p)) s++
  if (/[A-Z]/.test(p)) s++
  return s
})

// score is 0-5; map to 4 visual bars with thresholds ≤1 / 2 / 3-4 / 5
const scoreColor = computed(() => {
  if (score.value <= 1) return 'bg-destructive'
  if (score.value === 2) return 'bg-warning'
  if (score.value <= 4) return 'bg-info'
  return 'bg-success'
})

const labelColor = computed(() => {
  if (score.value <= 1) return 'text-destructive'
  if (score.value === 2) return 'text-warning'
  if (score.value <= 4) return 'text-info'
  return 'text-success'
})

const label = computed(() => {
  if (score.value <= 1) return t('common.passwordStrength.weak')
  if (score.value === 2) return t('common.passwordStrength.fair')
  if (score.value <= 4) return t('common.passwordStrength.good')
  return t('common.passwordStrength.strong')
})

// map 0-5 score to 0-4 filled bars
const bars = computed(() => Math.min(4, Math.round((score.value / 5) * 4)))
</script>
