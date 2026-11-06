<template>
  <div>
    <span class="text-sm font-medium">{{
      freeAsText && price.amount === 0 ? $t('subscription.free') : formatPrice(shown)
    }}</span>
    <span v-if="!freeAsText || price.amount > 0" class="text-xs text-muted-foreground">
      / {{ intervalLabel(shown) }}</span
    >
    <span v-if="billedYearly" class="block text-xs text-muted-foreground">{{
      $t('subscription.billedYearly', { price: billedYearly })
    }}</span>
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
// A yearly price is shown by the month, its yearly total under it (`displayedPrice`).
const props = defineProps<{ price: PlanPriceOut; freeAsText?: boolean; currency?: string }>()

const { formatPrice, intervalLabel, displayedPrice } = useBillingFormat()

const displayed = computed(() => displayedPrice(props.price))
const billedYearly = computed(() => displayed.value.billedYearly)

const shown = computed(() =>
  props.price.amount === 0 && props.currency
    ? { ...props.price, currency: props.currency }
    : displayed.value.price,
)
</script>
