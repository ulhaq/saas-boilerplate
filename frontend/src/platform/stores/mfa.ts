import { defineStore } from 'pinia'
import { mfaApi } from '@/platform/api/mfa'
import { useProfileStore } from '@/platform/stores/profile'
import type { MfaDisableIn, MfaSetupOut } from '@/platform/types'

// Gateway for the current user's two-factor enrollment; keeps
// profile.user.mfa_enabled in sync with the server.
export const useMfaStore = defineStore('mfa', () => {
  const profile = useProfileStore()

  function setEnabled(enabled: boolean): void {
    if (profile.user) profile.user.mfa_enabled = enabled
  }

  async function setup(): Promise<MfaSetupOut> {
    const { data } = await mfaApi.setup()
    return data
  }

  /** Confirms setup with a code; returns the one-time recovery codes. */
  async function enable(code: string): Promise<string[]> {
    const { data } = await mfaApi.enable({ code })
    setEnabled(true)
    return data.recovery_codes
  }

  async function disable(data: MfaDisableIn): Promise<void> {
    await mfaApi.disable(data)
    setEnabled(false)
  }

  async function regenerateRecoveryCodes(code: string): Promise<string[]> {
    const { data } = await mfaApi.regenerateRecoveryCodes({ code })
    return data.recovery_codes
  }

  return { setup, enable, disable, regenerateRecoveryCodes }
})
