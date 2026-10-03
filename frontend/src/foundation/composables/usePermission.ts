import { computed } from 'vue'
import { useProfileStore } from '@/foundation/stores/profile'
import { OWNER_ROLE_NAME } from '@/foundation/constants'

export function usePermission() {
  const profileStore = useProfileStore()

  const isOwner = computed(
    () =>
      profileStore.user?.roles.some((r) => r.is_protected && r.name === OWNER_ROLE_NAME) ?? false,
  )

  function hasPermission(permission: string): boolean {
    return profileStore.hasPermission(permission)
  }

  function hasAnyPermission(...permissions: string[]): boolean {
    return permissions.some((p) => profileStore.hasPermission(p))
  }

  return { hasPermission, hasAnyPermission, isOwner }
}
