import { useI18n } from 'vue-i18n'
import type { PlanOut, PlanPriceOut } from '@/platform/types'

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

  function formatPrice(price: PlanPriceOut): string {
    const amount = price.amount / 100
    try {
      return new Intl.NumberFormat(locale.value, {
        style: 'currency',
        currency: price.currency,
      }).format(amount)
    } catch {
      return `${price.currency.toUpperCase()} ${amount.toFixed(2)}`
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

  function statusBadgeVariant(status: string): BadgeVariant {
    return STATUS_BADGES[status] ?? 'outline'
  }

  return { formatPrice, planDescription, monthlyEquivalent, statusBadgeVariant }
}
