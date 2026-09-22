import { defineStore } from 'pinia'
import { ref } from 'vue'
import { usersApi } from '@/platform/api/users'
import { DEFAULT_LOCALE, i18n } from '@/plugins/i18n'
import type { UserOut, UserPatch, ChangePasswordIn, EmailChangeIn } from '@/platform/types'

export const useProfileStore = defineStore('profile', () => {
  const user = ref<UserOut | null>(null)
  const permissions = ref<string[]>([])

  function hasPermission(permission: string): boolean {
    return permissions.value.includes(permission)
  }

  async function fetchMe(): Promise<void> {
    const { data: me } = await usersApi.getMe()
    user.value = me
    permissions.value = [...new Set(me.roles.flatMap((r) => r.permissions.map((p) => p.name)))]
    i18n.global.locale.value = me.locale ?? DEFAULT_LOCALE
    localStorage.setItem('locale', i18n.global.locale.value)
    applyTheme((me.theme ?? 'system') as 'light' | 'dark' | 'system')
  }

  // Current-user ("me") write: calls the API and keeps the cached user in sync.
  async function updateMe(data: UserPatch): Promise<UserOut> {
    const { data: updated } = await usersApi.patchMe(data)
    user.value = updated
    return updated
  }

  async function changePassword(data: ChangePasswordIn): Promise<void> {
    await usersApi.changePassword(data)
  }

  // Nothing changes locally: the email only changes once the link sent to
  // the new address is confirmed.
  async function requestEmailChange(data: EmailChangeIn): Promise<void> {
    await usersApi.requestEmailChange(data)
  }

  function applyTheme(mode: 'light' | 'dark' | 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const dark = mode === 'dark' || (mode === 'system' && prefersDark)
    document.documentElement.classList.toggle('dark', dark)
  }

  function clear(): void {
    user.value = null
    permissions.value = []
  }

  return {
    user,
    permissions,
    hasPermission,
    fetchMe,
    updateMe,
    changePassword,
    requestEmailChange,
    clear,
  }
})
