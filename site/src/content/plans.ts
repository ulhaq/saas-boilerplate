import type { Locale } from '../i18n/routes'

/**
 * The plans shown on the pricing page. Static on purpose - the site is built
 * without access to the API - so keep it in sync with the plan seeds (the
 * initial migration + product migration) and `planComparisonRows` in the app's
 * product locales whenever prices or limits change.
 */
export const TRIAL_DAYS = 7 // backend BILLING_TRIAL_PERIOD_DAYS
/** The currencies the plans are priced in (the backend's plan prices), in the
 * order the pricing cards' currency switch lists them. */
export const CURRENCIES = ['DKK', 'EUR'] as const
export type Currency = (typeof CURRENCIES)[number]

/** The currency each locale's pages show until the visitor picks another, as the
 * app does: DKK in Danish, EUR otherwise. */
export const CURRENCY: Record<Locale, Currency> = { en: 'EUR', da: 'DKK' }

/** Plan highlighted as "most popular"; empty for none. */
export const RECOMMENDED_PLAN = 'Advanced'

export interface Plan {
  name: string
  /** Monthly price per currency in minor units (øre, cents); 0 is the free plan. */
  amount: Record<Currency, number>
  description: Record<Locale, string>
}

export const PLANS: Plan[] = [
  {
    name: 'Free',
    amount: { DKK: 0, EUR: 0 },
    description: { en: 'For individuals getting started', da: 'Til enkeltpersoner, der vil i gang' },
  },
  {
    name: 'Basic',
    amount: { DKK: 7900, EUR: 1100 },
    description: { en: 'For small teams', da: 'Til små teams' },
  },
  {
    name: 'Advanced',
    amount: { DKK: 19900, EUR: 2700 },
    description: {
      en: 'For growing teams that need API access',
      da: 'Til voksende teams med behov for API-adgang',
    },
  },
  {
    name: 'Pro',
    amount: { DKK: 49900, EUR: 6700 },
    description: { en: 'For large organizations', da: 'Til store organisationer' },
  },
]

type Cell = string | boolean

export interface ComparisonRow {
  label: string
  /** Stat rows (limits) are listed on every plan card. */
  stat?: boolean
  note?: string
  values: Record<string, Cell>
}

export const COMPARISON: Record<Locale, ComparisonRow[]> = {
  en: [
    {
      label: 'Projects',
      stat: true,
      values: { Free: '3', Basic: '20', Advanced: '100', Pro: 'Unlimited' },
    },
    { label: 'Users', stat: true, values: { Free: '1', Basic: '3', Advanced: '10', Pro: '50' } },
    {
      label: 'Roles and permissions',
      values: { Free: true, Basic: true, Advanced: true, Pro: true },
    },
    { label: 'Email notifications', values: { Free: true, Basic: true, Advanced: true, Pro: true } },
    { label: 'Audit log', values: { Free: true, Basic: true, Advanced: true, Pro: true } },
    {
      label: 'API tokens',
      note: 'Call the REST API from your own code or integrations',
      values: { Free: false, Basic: false, Advanced: true, Pro: true },
    },
  ],
  da: [
    {
      label: 'Projekter',
      stat: true,
      values: { Free: '3', Basic: '20', Advanced: '100', Pro: 'Ubegrænset' },
    },
    { label: 'Brugere', stat: true, values: { Free: '1', Basic: '3', Advanced: '10', Pro: '50' } },
    {
      label: 'Roller og tilladelser',
      values: { Free: true, Basic: true, Advanced: true, Pro: true },
    },
    { label: 'Emailnotifikationer', values: { Free: true, Basic: true, Advanced: true, Pro: true } },
    { label: 'Revisionslog', values: { Free: true, Basic: true, Advanced: true, Pro: true } },
    {
      label: 'API-tokens',
      note: 'Kald REST API’et fra din egen kode eller integrationer',
      values: { Free: false, Basic: false, Advanced: true, Pro: true },
    },
  ],
}

/** The plan's monthly price in minor units, in the locale's currency or `currency`. */
export function planAmount(plan: Plan, locale: Locale, currency: Currency = CURRENCY[locale]): number {
  return plan.amount[currency]
}

export function formatPrice(
  amount: number,
  locale: Locale,
  currency: Currency = CURRENCY[locale],
): string {
  return new Intl.NumberFormat(locale === 'da' ? 'da-DK' : 'en-IE', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount / 100)
}
