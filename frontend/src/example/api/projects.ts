import { apiClient } from '@/platform/api/client'
import type { PaginatedResponse } from '@/platform/types'
import type { ProjectIn, ProjectOut, ProjectPatch } from '@/example/types/project'

type ListParams = Record<string, string | number | undefined>

export const projectsApi = {
  list(params: ListParams = {}) {
    return apiClient.get<PaginatedResponse<ProjectOut>>('/projects', { params })
  },

  get(id: number) {
    return apiClient.get<ProjectOut>(`/projects/${id}`)
  },

  create(data: ProjectIn) {
    return apiClient.post<ProjectOut>('/projects', data)
  },

  patch(id: number, data: ProjectPatch) {
    return apiClient.patch<ProjectOut>(`/projects/${id}`, data)
  },

  remove(id: number) {
    return apiClient.delete(`/projects/${id}`)
  },
}
