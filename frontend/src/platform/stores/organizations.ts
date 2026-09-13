import { defineStore } from 'pinia'
import { ref } from 'vue'
import { organizationsApi } from '@/platform/api/organizations'
import type {
  OrganizationOut,
  OrganizationBase,
  OrganizationPatch,
  PaginatedResponse,
  UserOut,
} from '@/platform/types'

// Gateway store for the organizations domain (see frontend/CLAUDE.md "Data
// Access"). Components never import `@/platform/api/organizations` directly. Holds the
// current user's organization list (for the org switcher) and owns all org
// reads/writes.
export const useOrganizationsStore = defineStore('organizations', () => {
  const organizations = ref<OrganizationOut[]>([])

  async function fetchOrganizations(): Promise<void> {
    const { data: orgs } = await organizationsApi.list()
    organizations.value = orgs
  }

  async function get(id: number): Promise<OrganizationOut> {
    const { data: org } = await organizationsApi.get(id)
    return org
  }

  async function create(data: OrganizationBase): Promise<OrganizationOut> {
    const { data: org } = await organizationsApi.create(data)
    return org
  }

  async function patch(id: number, data: OrganizationPatch): Promise<OrganizationOut> {
    const { data: org } = await organizationsApi.patch(id, data)
    return org
  }

  async function remove(id: number): Promise<void> {
    await organizationsApi.delete(id)
  }

  async function getUsers(organizationId: number): Promise<PaginatedResponse<UserOut>> {
    const { data: users } = await organizationsApi.getUsers(organizationId)
    return users
  }

  async function transferOwnership(organizationId: number, userId: number): Promise<void> {
    await organizationsApi.transferOwnership(organizationId, userId)
  }

  function clear(): void {
    organizations.value = []
  }

  return {
    organizations,
    fetchOrganizations,
    get,
    create,
    patch,
    remove,
    getUsers,
    transferOwnership,
    clear,
  }
})
