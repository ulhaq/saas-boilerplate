<template>
  <div>
    <span class="text-sm font-medium">{{
      freeAsText && price.amount === 0 ? $t('subscription.free') : formatPrice(shown)
    }}</span>
    <span v-if="!freeAsText || price.amount > 0" class="text-xs text-muted-foreground">
      / {{ intervalLabel(shown) }}</span
    >
    <span v-if="price.amount > 0" class="block text-xs text-muted-foreground">{{
      $t('common.exclVat')
    }}</span>
    <span v-if="billed" class="block text-xs text-muted-foreground">{{ billed }}</span>
    <span
      v-if="saving || (reserveSaving && price.amount > 0)"
      :class="[
        'mt-1 inline-flex w-fit rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success',
        { invisible: !saving },
      ]"
      :aria-hidden="saving ? undefined : 'true'"
      >{{ saving ? $t('subscription.yearlySavingAmount', { amount: saving }) : '\u00a0' }}</span
    >
  </div>
</template>

<script setup lang="ts">
import { useBillingFormat } from '@/billing/composables/useBillingFormat'
import type { PlanPriceOut } from '@/billing/types'

// `freeAsText`: show a free price as "Free" with no interval. `currency`: the page's
// currency, used for a free price - the free plan has one price whatever the currency.
// A yearly price is shown by the month, how often it is billed under it (`displayedPrice`).
// `saving`: what this price saves a year over the plan's monthly one, formatted (none: no
// line). `reserveSaving`: keep the saving's room on a paid price without one, so a card
// keeps its height when the period switches.
const props = defineProps<{
  price: PlanPriceOut
  freeAsText?: boolean
  currency?: string
  saving?: string | null
  reserveSaving?: boolean
}>()

const { formatPrice, intervalLabel, displayedPrice } = useBillingFormat()

const displayed = computed(() => displayedPrice(props.price))
const billed = computed(() => displayed.value.billed)

const shown = computed(() =>
  props.price.amount === 0 && props.currency
    ? { ...props.price, currency: props.currency }
    : displayed.value.price,
)
</script>
