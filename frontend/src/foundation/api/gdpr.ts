import { api } from './client'
import type { Schema } from '@/foundation/types/api'

export type UserDataExport = Schema<'UserDataExportOut'>
export type DeleteMeIn = Schema<'DeleteMeIn'>

export const gdprApi = {
  exportMyData() {
    return api.get('/users/me/export')
  },

  deleteMyAccount(data: DeleteMeIn) {
    return api.delete('/users/me', { body: data })
  },
}
