import { defineStore } from 'pinia'
import { projectsApi } from '@/example/api/projects'
import type { PaginatedResponse } from '@/platform/types'
import type { ProjectIn, ProjectOut, ProjectPatch } from '@/example/types/project'

type ListParams = Record<string, string | number | undefined>

// Gateway store for projects: components never import `@/example/api/projects`
// directly. List state lives in `useDataTable`, so this store holds no cache.
export const useProjectsStore = defineStore('projects', () => {
  async function list(params: ListParams = {}): Promise<PaginatedResponse<ProjectOut>> {
    const { data: projects } = await projectsApi.list(params)
    return projects
  }

  async function get(id: number): Promise<ProjectOut> {
    const { data: project } = await projectsApi.get(id)
    return project
  }

  async function create(data: ProjectIn): Promise<ProjectOut> {
    const { data: project } = await projectsApi.create(data)
    return project
  }

  async function patch(id: number, data: ProjectPatch): Promise<ProjectOut> {
    const { data: project } = await projectsApi.patch(id, data)
    return project
  }

  async function remove(id: number): Promise<void> {
    await projectsApi.remove(id)
  }

  return { list, get, create, patch, remove }
})
