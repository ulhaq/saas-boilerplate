import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiTokensApi } from '@/platform/api/apiTokens'
import type { ApiTokenCreate, ApiTokenCreatedResponse, ApiTokenResponse } from '@/platform/types'

export const useApiTokensStore = defineStore('apiTokens', () => {
  const tokens = ref<ApiTokenResponse[]>([])

  async function fetchTokens(): Promise<void> {
    const { data: tokenList } = await apiTokensApi.list()
    tokens.value = tokenList
  }

  async function createToken(data: ApiTokenCreate): Promise<ApiTokenCreatedResponse> {
    const { data: created } = await apiTokensApi.create(data)
    const { token: _token, ...tokenRecord } = created
    tokens.value.unshift(tokenRecord)
    return created
  }

  async function revokeToken(id: number): Promise<void> {
    await apiTokensApi.revoke(id)
    tokens.value = tokens.value.filter((t) => t.id !== id)
  }

  return { tokens, fetchTokens, createToken, revokeToken }
})
