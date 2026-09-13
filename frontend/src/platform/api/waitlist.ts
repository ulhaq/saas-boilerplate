import { apiClient } from './client'

export interface WaitlistJoinIn {
  email: string
  name?: string | null
}

export interface WaitlistJoinOut {
  message: string
}

export const waitlistApi = {
  join(payload: WaitlistJoinIn) {
    return apiClient.post<WaitlistJoinOut>('/waitlist', payload)
  },
}
