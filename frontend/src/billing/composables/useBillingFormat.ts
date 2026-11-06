import { useI18n } from 'vue-i18n'
import type { PlanOut, PlanPriceOut } from '@/billing/types'

export type BadgeVariant = 'success' | 'info' | 'warning' | 'secondary' | 'error' | 'outline'

/** A row of the product's plan comparison table (`planComparisonRows` locale key). */
export type ComparisonRow = {
  label: string
  stat?: boolean
  details?: string[]
  [planName: string]: string | boolean | string[] | undefined
}

const STATUS_BADGES: Record<string, BadgeVariant> = {
  active: 'success',
  trialing: 'info',
  past_due: 'warning',
  paused: 'warning',
  canceled: 'secondary',
  incomplete: 'error',
}

/** Formatting shared by the billing page and its components. */
export function useBillingFormat() {
  const { t, te, locale } = useI18n()

  /** A price in its currency, as the marketing site writes it: whole amounts without
   * decimals (€12), others with two (€32.50). */
  function formatPrice(price: Pick<PlanPriceOut, 'amount' | 'currency'>): string {
    const amount = price.amount / 100
    const digits = price.amount % 100 === 0 ? 0 : 2
    try {
      return new Intl.NumberFormat(locale.value, {
        style: 'currency',
        currency: price.currency,
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(amount)
    } catch {
      return `${price.currency.toUpperCase()} ${amount.toFixed(digits)}`
    }
  }

  /** The product locale's text for the plan, else the plan's own description. */
  function planDescription(plan: PlanOut): string | null {
    const key = `planDescriptions.${plan.name}`
    return te(key) ? t(key) : plan.description
  }

  function monthlyEquivalent(price: PlanPriceOut): number {
    const count = price.interval_count ?? 1
    return price.interval === 'year' ? price.amount / (12 * count) : price.amount / count
  }

  /** How a price is shown: a yearly one by the month, as a monthly one is, with its yearly
   * total in `billedYearly` (else null), so the periods compare at a glance. */
  function displayedPrice(price: PlanPriceOut): {
    price: PlanPriceOut
    billedYearly: string | null
  } {
    if (price.amount === 0 || price.interval !== 'year') return { price, billedYearly: null }
    return {
      price: { ...price, amount: Math.round(monthlyEquivalent(price)), interval: 'month' },
      billedYearly: formatPrice(price),
    }
  }

  /** The price's billing period in the locale ("month", "year"), else Stripe's word. */
  function intervalLabel(price: Pick<PlanPriceOut, 'interval'>): string {
    const key = `subscription.intervals.${price.interval}`
    return te(key) ? t(key) : price.interval
  }

  function statusBadgeVariant(status: string): BadgeVariant {
    return STATUS_BADGES[status] ?? 'outline'
  }

  return {
    formatPrice,
    planDescription,
    monthlyEquivalent,
    displayedPrice,
    intervalLabel,
    statusBadgeVariant,
  }
}
