import { api } from './client'

type ListParams = Record<string, string | number | undefined>

export const permissionsApi = {
  list(params: ListParams = {}) {
    return api.get('/permissions', { query: params })
  },

  get(id: number) {
    return api.get('/permissions/{identifier}', { path: { identifier: id } })
  },
}
