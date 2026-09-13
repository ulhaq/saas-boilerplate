import type { SupportedLocale } from '@/plugins/i18n'
import type { RoleOut } from './role'

export interface UserBase {
  name: string
  email: string
}

export interface UserPatch {
  name?: string
  email?: string
  locale?: SupportedLocale
  theme?: string
}

export interface UserRoleIn {
  role_ids: number[]
}

export interface UserOut extends UserBase {
  id: number
  locale: SupportedLocale
  theme: string
  roles: RoleOut[]
  created_at: string
  updated_at: string
}
