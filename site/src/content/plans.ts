import type { Locale } from '../i18n/routes'

/**
 * The plans shown on the pricing page. Static on purpose - the site is built
 * without access to the API - so keep it in sync with the plan seeds (the
 * initial migration + product migration) and `planComparisonRows` in the app's
 * product locales whenever prices or limits change.
 */
export const TRIAL_DAYS = 7 // backend BILLING_TRIAL_PERIOD_DAYS
export const CURRENCY = 'DKK'

/** Plan highlighted as "most popular"; empty for none. */
export const RECOMMENDED_PLAN = 'Advanced'

export interface Plan {
  name: string
  /** Monthly price in minor units (øre); 0 is the free plan. */
  amount: number
  description: Record<Locale, string>
}

export const PLANS: Plan[] = [
  {
    name: 'Free',
    amount: 0,
    description: { en: 'For individuals getting started', da: 'Til enkeltpersoner, der vil i gang' },
  },
  {
    name: 'Basic',
    amount: 7900,
    description: { en: 'For small teams', da: 'Til små teams' },
  },
  {
    name: 'Advanced',
    amount: 19900,
    description: {
      en: 'For growing teams that need API access',
      da: 'Til voksende teams med behov for API-adgang',
    },
  },
  {
    name: 'Pro',
    amount: 49900,
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

export function formatPrice(amount: number, locale: Locale): string {
  return new Intl.NumberFormat(locale === 'da' ? 'da-DK' : 'en-DK', {
    style: 'currency',
    currency: CURRENCY,
    maximumFractionDigits: 0,
  }).format(amount / 100)
}
