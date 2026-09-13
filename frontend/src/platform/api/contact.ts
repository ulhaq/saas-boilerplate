import { apiClient } from './client'

export interface ContactMessageIn {
  name: string
  email: string
  subject: string
  message: string
  locale?: string | null
}

export interface ContactMessageOut {
  message: string
}

export const contactApi = {
  submit(payload: ContactMessageIn) {
    return apiClient.post<ContactMessageOut>('/contact', payload)
  },
}
