import { api } from './client'
import type { MfaCodeIn, MfaDisableIn } from '@/platform/types'

export const mfaApi = {
  setup() {
    return api.post('/users/me/mfa/setup')
  },

  enable(data: MfaCodeIn) {
    return api.post('/users/me/mfa/enable', { body: data })
  },

  disable(data: MfaDisableIn) {
    return api.post('/users/me/mfa/disable', { body: data })
  },

  regenerateRecoveryCodes(data: MfaCodeIn) {
    return api.post('/users/me/mfa/recovery-codes', { body: data })
  },
}
