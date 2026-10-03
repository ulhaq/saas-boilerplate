import { api } from './client'
import type { ApiTokenCreate } from '@/foundation/types'

export const apiTokensApi = {
  list() {
    return api.get('/api-tokens')
  },

  create(data: ApiTokenCreate) {
    return api.post('/api-tokens', { body: data })
  },

  revoke(id: number) {
    return api.delete('/api-tokens/{token_id}', { path: { token_id: id } })
  },
}
