import { api } from './client'
import type { OrganizationBase, OrganizationPatch } from '@/foundation/types'

export const organizationsApi = {
  list() {
    return api.get('/organizations')
  },

  get(id: number) {
    return api.get('/organizations/{identifier}', { path: { identifier: id } })
  },

  create(data: OrganizationBase) {
    return api.post('/organizations', { body: data })
  },

  patch(id: number, data: OrganizationPatch) {
    return api.patch('/organizations/{identifier}', { path: { identifier: id }, body: data })
  },

  delete(id: number) {
    return api.delete('/organizations/{identifier}', { path: { identifier: id } })
  },

  getUsers(organizationId: number) {
    return api.get('/organizations/{organization_id}/users', {
      path: { organization_id: organizationId },
    })
  },

  transferOwnership(organizationId: number, userId: number) {
    return api.post('/organizations/{organization_id}/transfer-ownership', {
      path: { organization_id: organizationId },
      body: { user_id: userId },
    })
  },
}
