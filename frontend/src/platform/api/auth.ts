import { apiClient } from './client'
import type {
  Token,
  RegisterIn,
  RegisterOut,
  VerifyEmailIn,
  VerifyEmailOut,
  CompleteRegistrationIn,
  CompleteInviteIn,
  InviteStatusResponse,
  ResetPasswordRequestIn,
  ResetPasswordIn,
  SwitchOrganizationIn,
} from '@/platform/types'

export const authApi = {
  login(email: string, password: string) {
    const form = new URLSearchParams()
    form.append('username', email) // OAuth2 spec uses 'username'
    form.append('password', password)
    return apiClient.post<Token>('/auth/token', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },

  register(data: RegisterIn) {
    return apiClient.post<RegisterOut>('/auth/register', data)
  },

  verifyEmail(data: VerifyEmailIn) {
    return apiClient.post<VerifyEmailOut>('/auth/verify-email', data)
  },

  completeRegistration(data: CompleteRegistrationIn) {
    return apiClient.post<Token>('/auth/complete-registration', data)
  },

  logout() {
    return apiClient.post('/auth/logout')
  },

  refresh() {
    return apiClient.post<Token>('/auth/refresh')
  },

  requestPasswordReset(data: ResetPasswordRequestIn) {
    return apiClient.post('/auth/reset-password/request', data)
  },

  resetPassword(data: ResetPasswordIn) {
    return apiClient.post('/auth/reset-password', data)
  },

  switchOrganization(data: SwitchOrganizationIn) {
    return apiClient.post<Token>('/auth/switch-organization', data)
  },

  inviteStatus(token: string) {
    return apiClient.post<InviteStatusResponse>('/auth/invite-status', { token })
  },

  completeInvite(data: CompleteInviteIn) {
    return apiClient.post<Token>('/auth/complete-invite', data)
  },
}
