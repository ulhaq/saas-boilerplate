<template>
  <div class="text-xl font-semibold">
    {{ formatPrice(shown) }}
    <span class="text-sm font-normal text-muted-foreground">/ {{ price.interval }}</span>
    <span v-if="price.amount > 0" class="block text-xs font-normal text-muted-foreground">{{
      $t('common.exclVat')
    }}</span>
  </div>
</template>

<script setup lang="ts">
import { useBillingFormat } from '@/billing/composables/useBillingFormat'
import type { PlanPriceOut } from '@/billing/types'

// `currency`: the page's currency, used for a free price - the free plan has one price
// whatever the currency, so 0 is shown in the one the plans are offered in.
const props = defineProps<{ price: PlanPriceOut; currency?: string }>()

const { formatPrice } = useBillingFormat()

const shown = computed(() =>
  props.price.amount === 0 && props.currency
    ? { ...props.price, currency: props.currency }
    : props.price,
)
</script>
