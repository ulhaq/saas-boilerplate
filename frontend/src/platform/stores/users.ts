import { defineStore } from 'pinia'
import { usersApi } from '@/platform/api/users'
import type { PaginatedResponse, UserOut, UserPatch, UserRoleIn } from '@/platform/types'

type ListParams = Record<string, string | number | undefined>

// Gateway store for the user-management domain (see frontend/CLAUDE.md "Data
// Access"). Components never import `@/platform/api/users` directly. Current-user ("me")
// operations live in the `profile` store; this store is the admin surface.
export const useUsersStore = defineStore('users', () => {
  async function list(params: ListParams = {}): Promise<PaginatedResponse<UserOut>> {
    const { data: users } = await usersApi.list(params)
    return users
  }

  async function patch(id: number, data: UserPatch): Promise<UserOut> {
    const { data: user } = await usersApi.patch(id, data)
    return user
  }

  async function setRoles(id: number, data: UserRoleIn): Promise<UserOut> {
    const { data: user } = await usersApi.setRoles(id, data)
    return user
  }

  async function invite(data: { email: string; role_ids: number[] }): Promise<void> {
    await usersApi.invite(data)
  }

  async function removeFromOrganization(id: number): Promise<void> {
    await usersApi.removeFromOrganization(id)
  }

  return { list, patch, setRoles, invite, removeFromOrganization }
})
