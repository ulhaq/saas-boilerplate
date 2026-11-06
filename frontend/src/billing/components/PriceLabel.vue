<template>
  <div>
    <span class="text-sm font-medium">{{
      freeAsText && price.amount === 0 ? $t('subscription.free') : formatPrice(shown)
    }}</span>
    <span v-if="!freeAsText || price.amount > 0" class="text-xs text-muted-foreground">
      / {{ price.interval }}</span
    >
    <span v-if="price.amount > 0" class="block text-xs text-muted-foreground">{{
      $t('common.exclVat')
    }}</span>
  </div>
</template>

<script setup lang="ts">
import { useBillingFormat } from '@/billing/composables/useBillingFormat'
import type { PlanPriceOut } from '@/billing/types'

// `freeAsText`: show a free price as "Free" with no interval. `currency`: the page's
// currency, used for a free price - the free plan has one price whatever the currency.
const props = defineProps<{ price: PlanPriceOut; freeAsText?: boolean; currency?: string }>()

const { formatPrice } = useBillingFormat()

const shown = computed(() =>
  props.price.amount === 0 && props.currency
    ? { ...props.price, currency: props.currency }
    : props.price,
)
</script>
