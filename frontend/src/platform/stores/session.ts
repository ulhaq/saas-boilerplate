import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { setAccessToken } from '@/platform/api/client'

function parseJwtClaim(token: string, claim: string): unknown {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload[claim]
  } catch {
    return null
  }
}

export const useSessionStore = defineStore('session', () => {
  const accessToken = ref<string | null>(null)
  const isInitialized = ref(false)
  const isAuthenticated = computed(() => !!accessToken.value)
  const activeOrganizationId = computed<number | null>(() =>
    accessToken.value ? (parseJwtClaim(accessToken.value, 'oid') as number | null) : null,
  )

  function setToken(token: string | null): void {
    accessToken.value = token
    setAccessToken(token)
  }

  function clear(): void {
    accessToken.value = null
    setAccessToken(null)
  }

  return { accessToken, isInitialized, isAuthenticated, activeOrganizationId, setToken, clear }
})
