export interface ProjectOut {
  id: number
  organization_id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface ProjectIn {
  name: string
  description?: string | null
}

export type ProjectPatch = Partial<ProjectIn>
