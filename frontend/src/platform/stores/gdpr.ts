import { defineStore } from 'pinia'
import { gdprApi, type UserDataExport, type DeleteMeIn } from '@/platform/api/gdpr'

// Gateway store for the GDPR self-service domain (see frontend/CLAUDE.md "Data
// Access"). Components never import `@/platform/api/gdpr` directly.
export const useGdprStore = defineStore('gdpr', () => {
  async function exportMyData(): Promise<UserDataExport> {
    const { data: exportData } = await gdprApi.exportMyData()
    return exportData
  }

  async function deleteMyAccount(data: DeleteMeIn): Promise<void> {
    await gdprApi.deleteMyAccount(data)
  }

  return { exportMyData, deleteMyAccount }
})
