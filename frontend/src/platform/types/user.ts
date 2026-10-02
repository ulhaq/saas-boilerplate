import type { Schema } from './api'

export type UserPatch = Schema<'UserPatch'>
export type EmailChangeIn = Schema<'EmailChangeIn'>
export type UserRoleIn = Schema<'UserRoleIn'>

export type UserOut = Schema<'UserOut'>
export type UserBase = Pick<UserOut, 'name' | 'email'>
