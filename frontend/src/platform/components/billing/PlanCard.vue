<template>
  <div class="rounded-lg border p-4 space-y-3">
    <div v-if="$slots.badge" class="flex items-start justify-between gap-2">
      <div>
        <h4 class="font-semibold">{{ plan.name }}</h4>
        <p class="text-xs text-muted-foreground mt-0.5">
          {{ planDescription(plan) }}
        </p>
      </div>
      <slot name="badge" />
    </div>
    <div v-else>
      <h4 class="font-semibold">{{ plan.name }}</h4>
      <p v-if="plan.description" class="text-xs text-muted-foreground mt-0.5">
        {{ planDescription(plan) }}
      </p>
    </div>
    <PlanFeatures :plan-name="plan.name" :rows="rows" />
    <slot />
  </div>
</template>

<script setup lang="ts">
import PlanFeatures from './PlanFeatures.vue'
import { useBillingFormat, type ComparisonRow } from '@/platform/composables/useBillingFormat'
import type { PlanOut } from '@/platform/types'

defineProps<{ plan: PlanOut; rows: ComparisonRow[] }>()

const { planDescription } = useBillingFormat()
</script>
