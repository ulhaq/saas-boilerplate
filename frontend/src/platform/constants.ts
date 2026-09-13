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

// Swagger UI served by the API process itself, so it lives on the API host
// rather than behind the app's `/v1` proxy. Overridable per environment.
export const API_DOCS_URL =
  (import.meta.env.VITE_API_DOCS_URL as string | undefined) ?? BRAND.apiDocsUrl
