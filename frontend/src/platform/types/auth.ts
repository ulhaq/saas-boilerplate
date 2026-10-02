import type { Schema } from './api'

export type Token = Schema<'Token'>

// Returned instead of a Token when the account has two-factor auth enabled;
// exchange it (plus a code) for a Token via POST /auth/mfa/verify.
export type MfaChallenge = Schema<'MfaChallengeOut'>

export type MfaVerifyIn = Schema<'MfaVerifyIn'>

export interface LoginIn {
  username: string
  password: string
}

export type ResetPasswordRequestIn = Schema<'EmailIn'>

export type ResetPasswordIn = Schema<'ResetPasswordIn'>

export type ChangePasswordIn = Schema<'ChangePasswordIn'>

export type SwitchOrganizationIn = Schema<'SwitchOrganizationIn'>

export type RegisterIn = Schema<'RegisterIn'>

export type RegisterOut = Schema<'RegisterOut'>

export type VerifyEmailIn = Schema<'VerifyEmailIn'>

export type VerifyEmailOut = Schema<'SetupTokenOut'>

export type CompleteRegistrationIn = Schema<'CompleteRegistrationIn'>

export type CompleteInviteIn = Schema<'CompleteInviteIn'>

export type InviteStatusResponse = Schema<'InviteStatusOut'>

export interface JwtPayload {
  sub: string
  name?: string
  email?: string
  oid?: number
  permissions?: string[]
  exp: number
  iat: number
  jti: string
}
