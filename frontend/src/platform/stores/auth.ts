import { defineStore } from 'pinia'
import { computed } from 'vue'
import { authApi } from '@/platform/api/auth'
import { useSessionStore } from '@/platform/stores/session'
import { useProfileStore } from '@/platform/stores/profile'
import { useOrganizationsStore } from '@/platform/stores/organizations'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useNotificationsStore } from '@/platform/stores/notifications'
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
} from '@/platform/types'

export const useAuthStore = defineStore('auth', () => {
  const session = useSessionStore()
  const profile = useProfileStore()
  const organizationStore = useOrganizationsStore()
  const subscription = useSubscriptionStore()
  const notificationsStore = useNotificationsStore()

  const isInitialized = computed(() => session.isInitialized)
  const isAuthenticated = computed(() => session.isAuthenticated)
  const hasActiveSubscription = computed(() => subscription.hasActiveSubscription)
  const hasAppAccess = computed(() => subscription.hasAppAccess)

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
      subscription.fetchSubscriptionStatus(),
    ])
    notificationsStore.startPolling()
  }

  function clearSession(): void {
    session.clear()
    profile.clear()
    organizationStore.clear()
    subscription.clear()
    notificationsStore.clear()
  }

  async function initialize(): Promise<void> {
    try {
      const { data: token } = await authApi.refresh()
      session.setToken(token.access_token)
      await Promise.all([
        profile.fetchMe(),
        organizationStore.fetchOrganizations(),
        subscription.fetchSubscriptionStatus(),
      ])
      notificationsStore.startPolling()
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

  // Accepts an org invite, establishes the session, and bootstraps app state
  // (mirrors login: an existing account with 2FA gets an MfaChallenge).
  async function completeInvite(data: CompleteInviteIn): Promise<MfaChallenge | null> {
    const { data: res } = await authApi.completeInvite(data)
    if (isMfaChallenge(res)) return res
    await startSession(res)
    return null
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

  async function switchOrganization(organizationId: number): Promise<void> {
    const { data: token } = await authApi.switchOrganization({ organization_id: organizationId })
    setSession(token)
    await Promise.all([profile.fetchMe(), subscription.fetchSubscriptionStatus()])
    notificationsStore.clear()
    notificationsStore.startPolling()
    // organizations list does not change on switch
  }

  return {
    isInitialized,
    isAuthenticated,
    hasActiveSubscription,
    hasAppAccess,
    setSession,
    clearSession,
    initialize,
    login,
    verifyMfa,
    logout,
    completeRegistration,
    completeInvite,
    register,
    verifyEmail,
    inviteStatus,
    requestPasswordReset,
    resetPassword,
    switchOrganization,
  }
})
