import { api } from './client'
import type {
  MfaVerifyIn,
  RegisterIn,
  VerifyEmailIn,
  CompleteRegistrationIn,
  CompleteInviteIn,
  ResetPasswordRequestIn,
  ResetPasswordIn,
  SwitchOrganizationIn,
} from '@/foundation/types'

export const authApi = {
  login(email: string, password: string) {
    // OAuth2 password form: the email goes in `username`.
    return api.post('/auth/token', { form: { username: email, password } })
  },

  verifyMfa(data: MfaVerifyIn) {
    return api.post('/auth/mfa/verify', { body: data })
  },

  register(data: RegisterIn) {
    return api.post('/auth/register', { body: data })
  },

  verifyEmail(data: VerifyEmailIn) {
    return api.post('/auth/verify-email', { body: data })
  },

  completeRegistration(data: CompleteRegistrationIn) {
    return api.post('/auth/complete-registration', { body: data })
  },

  logout() {
    return api.post('/auth/logout')
  },

  refresh() {
    return api.post('/auth/refresh')
  },

  requestPasswordReset(data: ResetPasswordRequestIn) {
    return api.post('/auth/reset-password/request', { body: data })
  },

  resetPassword(data: ResetPasswordIn) {
    return api.post('/auth/reset-password', { body: data })
  },

  confirmEmailChange(token: string) {
    return api.post('/auth/confirm-email-change', { body: { token } })
  },

  switchOrganization(data: SwitchOrganizationIn) {
    return api.post('/auth/switch-organization', { body: data })
  },

  inviteStatus(token: string) {
    return api.post('/auth/invite-status', { body: { token } })
  },

  completeInvite(data: CompleteInviteIn) {
    return api.post('/auth/complete-invite', { body: data })
  },

  // Existing accounts: accept as the signed-in user (switches the session to
  // the invited organization).
  acceptInvite(inviteToken: string) {
    return api.post('/auth/accept-invite', { body: { invite_token: inviteToken } })
  },
}
