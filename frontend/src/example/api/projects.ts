import { api } from '@/foundation/api/client'
import type { ProjectIn, ProjectPatch } from '@/example/types/project'

type ListParams = Record<string, string | number | undefined>

export const projectsApi = {
  list(params: ListParams = {}) {
    return api.get('/projects', { query: params })
  },

  get(id: number) {
    return api.get('/projects/{project_id}', { path: { project_id: id } })
  },

  create(data: ProjectIn) {
    return api.post('/projects', { body: data })
  },

  patch(id: number, data: ProjectPatch) {
    return api.patch('/projects/{project_id}', { path: { project_id: id }, body: data })
  },

  remove(id: number) {
    return api.delete('/projects/{project_id}', { path: { project_id: id } })
  },
}
