export interface MfaSetupOut {
  secret: string
  otpauth_uri: string
}

export interface MfaCodeIn {
  code: string
}

export interface MfaDisableIn {
  password: string
  code: string
}

export interface MfaRecoveryCodesOut {
  recovery_codes: string[]
}
