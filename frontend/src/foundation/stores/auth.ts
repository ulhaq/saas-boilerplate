import { defineStore } from 'pinia'
import { computed } from 'vue'
import { authApi } from '@/foundation/api/auth'
import { useSessionStore } from '@/foundation/stores/session'
import { useProfileStore } from '@/foundation/stores/profile'
import { useOrganizationsStore } from '@/foundation/stores/organizations'
import { useEntitlements } from '@/foundation/entitlements'
import { useNotificationsStore } from '@/foundation/stores/notifications'
import { useRealtimeStore } from '@/foundation/stores/realtime'
import type {
  Token,
  MfaChallenge,
  RegisterIn,
  RegisterOut,
  VerifyEmailIn,
  VerifyEmailOut,
  CompleteInviteIn,
  InviteStatusResponse,
  ResetPasswordRequestIn,
  ResetPasswordIn,
} from '@/foundation/types'

export const useAuthStore = defineStore('auth', () => {
  const session = useSessionStore()
  const profile = useProfileStore()
  const organizationStore = useOrganizationsStore()
  const entitlements = useEntitlements()
  const notificationsStore = useNotificationsStore()
  const realtime = useRealtimeStore()

  const isInitialized = computed(() => session.isInitialized)
  const isAuthenticated = computed(() => session.isAuthenticated)

  function setSession(token: Token): void {
    session.setToken(token.access_token)
  }

  function isMfaChallenge(res: Token | MfaChallenge): res is MfaChallenge {
    return 'mfa_required' in res && res.mfa_required === true
  }

  // Establishes the session and bootstraps app state after any sign-in.
  async function startSession(token: Token): Promise<void> {
    setSession(token)
    await Promise.all([
      profile.fetchMe(),
      organizationStore.fetchOrganizations(),
      entitlements.load(),
    ])
    startLiveUpdates()
  }

  // The realtime stream is opened with the current access token, so (re)start
  // it whenever the session changes.
  function startLiveUpdates(): void {
    notificationsStore.start()
    realtime.connect()
  }

  function clearSession(): void {
    realtime.disconnect()
    session.clear()
    profile.clear()
    organizationStore.clear()
    entitlements.clear()
    notificationsStore.clear()
  }

  async function initialize(): Promise<void> {
    try {
      const { data: token } = await authApi.refresh()
      session.setToken(token.access_token)
      await Promise.all([
        profile.fetchMe(),
        organizationStore.fetchOrganizations(),
        entitlements.load(),
      ])
      startLiveUpdates()
    } catch {
      // No valid session cookie - proceed as unauthenticated.
    }
    session.isInitialized = true
  }

  // Returns an MfaChallenge (no session yet) when the account has 2FA on;
  // finish with verifyMfa().
  async function login(email: string, password: string): Promise<MfaChallenge | null> {
    const { data } = await authApi.login(email, password)
    if (isMfaChallenge(data)) return data
    await startSession(data)
    return null
  }

  async function verifyMfa(mfaToken: string, code: string): Promise<void> {
    const { data: token } = await authApi.verifyMfa({ mfa_token: mfaToken, code })
    await startSession(token)
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // ignore
    }
    clearSession()
  }

  async function completeRegistration(
    setupToken: string,
    name: string,
    password: string,
  ): Promise<void> {
    const { data: token } = await authApi.completeRegistration({
      setup_token: setupToken,
      name,
      password,
    })
    await startSession(token)
  }

  // New account from an invite: creates the user, establishes the session,
  // and bootstraps app state (mirrors completeRegistration).
  async function completeInvite(data: CompleteInviteIn): Promise<void> {
    const { data: token } = await authApi.completeInvite(data)
    await startSession(token)
  }

  // Existing account: joins the invited org as the signed-in user; the
  // returned session is scoped to the new org.
  async function acceptInvite(inviteToken: string): Promise<void> {
    const { data: token } = await authApi.acceptInvite(inviteToken)
    notificationsStore.clear()
    await startSession(token)
  }

  // --- unauthenticated passthrough flows (no session side effects) ---

  async function register(data: RegisterIn): Promise<RegisterOut> {
    const { data: out } = await authApi.register(data)
    return out
  }

  async function verifyEmail(data: VerifyEmailIn): Promise<VerifyEmailOut> {
    const { data: out } = await authApi.verifyEmail(data)
    return out
  }

  async function inviteStatus(token: string): Promise<InviteStatusResponse> {
    const { data: status } = await authApi.inviteStatus(token)
    return status
  }

  async function requestPasswordReset(data: ResetPasswordRequestIn): Promise<void> {
    await authApi.requestPasswordReset(data)
  }

  async function resetPassword(data: ResetPasswordIn): Promise<void> {
    await authApi.resetPassword(data)
  }

  // Applies an email change from its confirmation link. The server ends
  // every session, so any local one is dropped too.
  async function confirmEmailChange(token: string): Promise<void> {
    await authApi.confirmEmailChange(token)
    clearSession()
  }

  async function switchOrganization(organizationId: number): Promise<void> {
    const { data: token } = await authApi.switchOrganization({ organization_id: organizationId })
    setSession(token)
    await Promise.all([profile.fetchMe(), entitlements.load()])
    notificationsStore.clear()
    startLiveUpdates()
    // organizations list does not change on switch
  }

  return {
    isInitialized,
    isAuthenticated,
    setSession,
    clearSession,
    initialize,
    login,
    verifyMfa,
    logout,
    completeRegistration,
    completeInvite,
    acceptInvite,
    register,
    verifyEmail,
    inviteStatus,
    requestPasswordReset,
    resetPassword,
    confirmEmailChange,
    switchOrganization,
  }
})
