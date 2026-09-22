import { apiClient } from './client'
import type { MfaCodeIn, MfaDisableIn, MfaRecoveryCodesOut, MfaSetupOut } from '@/platform/types'

export const mfaApi = {
  setup() {
    return apiClient.post<MfaSetupOut>('/users/me/mfa/setup')
  },

  enable(data: MfaCodeIn) {
    return apiClient.post<MfaRecoveryCodesOut>('/users/me/mfa/enable', data)
  },

  disable(data: MfaDisableIn) {
    return apiClient.post('/users/me/mfa/disable', data)
  },

  regenerateRecoveryCodes(data: MfaCodeIn) {
    return apiClient.post<MfaRecoveryCodesOut>('/users/me/mfa/recovery-codes', data)
  },
}
