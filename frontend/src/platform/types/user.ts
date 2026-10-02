import type { SupportedLocale } from '@/plugins/i18n'
import type { Schema } from './api'

export type UserPatch = Schema<'UserPatch'>
export type EmailChangeIn = Schema<'EmailChangeIn'>
export type UserRoleIn = Schema<'UserRoleIn'>

// Narrowed beyond the API: the backend declares `locale` as a plain string.
export type UserOut = Omit<Schema<'UserOut'>, 'locale'> & { locale: SupportedLocale }
export type UserBase = Pick<UserOut, 'name' | 'email'>
