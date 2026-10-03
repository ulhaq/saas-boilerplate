import { api } from './client'
import type { UserPatch, UserRoleIn, ChangePasswordIn, EmailChangeIn } from '@/foundation/types'

type ListParams = Record<string, string | number | undefined>

export const usersApi = {
  list(params: ListParams = {}) {
    return api.get('/users', { query: params })
  },

  getMe() {
    return api.get('/users/me')
  },

  getMyOrganizations() {
    return api.get('/organizations')
  },

  get(id: number) {
    return api.get('/users/{identifier}', { path: { identifier: id } })
  },

  patch(id: number, data: UserPatch) {
    return api.patch('/users/{identifier}', { path: { identifier: id }, body: data })
  },

  patchMe(data: UserPatch) {
    return api.patch('/users/me', { body: data })
  },

  // Sends a confirmation link to the new address; the email changes only
  // once that link is confirmed (authApi.confirmEmailChange).
  requestEmailChange(data: EmailChangeIn) {
    return api.post('/users/me/email', { body: data })
  },

  changePassword(data: ChangePasswordIn) {
    return api.post('/users/me/change-password', { body: data })
  },

  removeFromOrganization(id: number) {
    return api.delete('/users/{identifier}', { path: { identifier: id } })
  },

  setRoles(id: number, data: UserRoleIn) {
    return api.post('/users/{identifier}/roles', { path: { identifier: id }, body: data })
  },

  invite(data: { email: string; role_ids: number[] }) {
    return api.post('/users/invite', { body: data })
  },
}
