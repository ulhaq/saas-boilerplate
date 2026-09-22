import type { SupportedLocale } from '@/plugins/i18n'
import type { RoleOut } from './role'

export interface UserBase {
  name: string
  email: string
}

// Email isn't patchable (the API rejects it); see EmailChangeIn.
export interface UserPatch {
  name?: string
  locale?: SupportedLocale
  theme?: string
}

export interface EmailChangeIn {
  new_email: string
  password: string
  /** Required when two-factor auth is on: TOTP or recovery code. */
  code?: string
}

export interface UserRoleIn {
  role_ids: number[]
}

export interface UserOut extends UserBase {
  id: number
  locale: SupportedLocale
  theme: string
  mfa_enabled: boolean
  roles: RoleOut[]
  created_at: string
  updated_at: string
}
