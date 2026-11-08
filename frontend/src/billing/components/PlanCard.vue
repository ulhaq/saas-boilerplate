<template>
  <!-- Side by side (sm+), the cards of a row share their rows (subgrid): name, prices, each
       feature row and the actions start at the same height on every card. -->
  <div
    class="grid gap-y-1.5 rounded-lg border p-4 sm:row-span-(--plan-rows) sm:grid-rows-subgrid"
    :style="{ '--plan-rows': rows.length + 3 }"
  >
    <div v-if="$slots.badge" class="mb-1.5 flex items-start justify-between gap-2">
      <div>
        <h4 class="font-semibold">{{ plan.name }}</h4>
        <p v-if="description" class="text-xs text-muted-foreground mt-0.5">
          {{ description }}
        </p>
      </div>
      <slot name="badge" />
    </div>
    <div v-else class="mb-1.5">
      <h4 class="font-semibold">{{ plan.name }}</h4>
      <p v-if="description" class="text-xs text-muted-foreground mt-0.5">
        {{ description }}
      </p>
    </div>
    <!-- The prices first, under the name, then what the plan includes; the actions (the
         default slot) at the bottom. Each always renders, so every card has the same rows. -->
    <div class="mb-1.5">
      <slot name="price" />
    </div>
    <PlanFeatures :plan-name="plan.name" :rows="rows" />
    <div class="self-end pt-3">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import PlanFeatures from './PlanFeatures.vue'
import { useBillingFormat, type ComparisonRow } from '@/billing/composables/useBillingFormat'
import type { PlanOut } from '@/billing/types'

const props = defineProps<{ plan: PlanOut; rows: ComparisonRow[] }>()

const { planDescription } = useBillingFormat()
const description = computed(() => planDescription(props.plan))
</script>
