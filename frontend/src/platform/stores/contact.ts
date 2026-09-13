import { defineStore } from 'pinia'
import { contactApi, type ContactMessageIn, type ContactMessageOut } from '@/platform/api/contact'

// Gateway store for the public contact form (see frontend/CLAUDE.md "Data
// Access"). Components never import `@/platform/api/contact` directly.
export const useContactStore = defineStore('contact', () => {
  async function submit(payload: ContactMessageIn): Promise<ContactMessageOut> {
    const { data } = await contactApi.submit(payload)
    return data
  }

  return { submit }
})
