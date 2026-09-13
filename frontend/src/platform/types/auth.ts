export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginIn {
  username: string
  password: string
}

export interface ResetPasswordRequestIn {
  email: string
}

export interface ResetPasswordIn {
  token: string
  password: string
}

export interface ChangePasswordIn {
  password: string
  new_password: string
  confirm_password: string
}

export interface SwitchOrganizationIn {
  organization_id: number
}

export interface RegisterIn {
  email: string
  terms_accepted: boolean
  locale?: string
}

export interface RegisterOut {
  message: string
}

export interface VerifyEmailIn {
  token: string
}

export interface VerifyEmailOut {
  setup_token: string
}

export interface CompleteRegistrationIn {
  setup_token: string
  name: string
  password: string
}

export interface CompleteInviteIn {
  invite_token: string
  name?: string
  password?: string
  terms_accepted?: boolean
}

export interface InviteStatusResponse {
  email: string
  user_exists: boolean
}

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
