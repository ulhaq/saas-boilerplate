import { BRAND } from '@/brand'

export const OWNER_ROLE_NAME = 'Owner'

export const PlanFeature = {
  API_TOKEN: 'api_token',
} as const

// Product modules define their own feature constants; values are validated
// against the org's plan at runtime, so the type stays open.
export type PlanFeatureValue = string
export const PASSWORD_MIN_LENGTH = 8

export const PAGE_SIZE = 100
export const PAGE_SIZE_DASHBOARD = 10

export const BADGE_MAX = 4

export const MS_PER_DAY = 24 * 60 * 60 * 1000

// Feature flag mirroring the backend `ALLOW_MULTIPLE_ORGANIZATIONS` setting.
// When false, the UI hides affordances for creating additional organizations
// (the backend enforces the actual guard). Defaults to enabled.
export const ALLOW_MULTIPLE_ORGANIZATIONS =
  import.meta.env.VITE_ALLOW_MULTIPLE_ORGANIZATIONS !== 'false'

// Feature flag mirroring the backend `MFA_ENABLED` setting: shows the
// two-factor section in security settings. Login handles MFA challenges from
// the API regardless of this flag. Defaults to disabled.
export const MFA_ENABLED = import.meta.env.VITE_MFA_ENABLED === 'true'

// The marketing site (`site/`), which hosts the legal pages.
// Overridable per environment.
export const MARKETING_ORIGIN: string =
  (import.meta.env.VITE_MARKETING_ORIGIN as string | undefined) || BRAND.marketingOrigin

// Legal page paths on the marketing site - keep in sync with `PAGES` in site/src/i18n/routes.ts.
const LEGAL_PATHS = {
  terms: { da: '/da/handelsbetingelser', en: '/en/terms' },
  privacy: { da: '/da/privatlivspolitik', en: '/en/privacy-policy' },
} as const

/** `legalUrl('terms', 'en')` -> `https://example.com/en/terms`; falls back to Danish. */
export function legalUrl(page: keyof typeof LEGAL_PATHS, locale: string): string {
  const paths = LEGAL_PATHS[page]
  return `${MARKETING_ORIGIN}${locale in paths ? paths[locale as keyof typeof paths] : paths.da}`
}
