<template>
  <div class="text-xl font-semibold">
    {{ formatPrice(price) }}
    <span class="text-sm font-normal text-muted-foreground">/ {{ price.interval }}</span>
    <span v-if="price.amount > 0" class="block text-xs font-normal text-muted-foreground">{{
      $t('common.exclVat')
    }}</span>
  </div>
</template>

<script setup lang="ts">
import { useBillingFormat } from '@/platform/composables/useBillingFormat'
import type { PlanPriceOut } from '@/platform/types'

defineProps<{ price: PlanPriceOut }>()

const { formatPrice } = useBillingFormat()
</script>
