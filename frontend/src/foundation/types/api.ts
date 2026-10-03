import type { components } from '@/api-schema'

/**
 * A backend schema by name. `src/api-schema.ts` is generated from the API
 * (`npm run gen:api`), so these types cannot drift from the backend.
 */
export type Schema<K extends keyof components['schemas']> = components['schemas'][K]

// Same shape as every generated `PaginatedResponse_<Item>_` schema.
export interface PaginatedResponse<T> {
  items: T[]
  page_number: number
  page_size: number
  total: number
}

export type FilterOp =
  | 'eq'
  | 'neq'
  | 'lt'
  | 'lte'
  | 'gt'
  | 'gte'
  | 'co'
  | 'ico'
  | 'nco'
  | 'inco'
  | 'in'
  | 'nin'
  | 'between'

export type ApiError = Schema<'ErrorResponse'>

export type FieldError = Schema<'ValidationDetail'>

// Every error body is an ErrorResponse; validation errors add `errors`.
export type ApiErrorResponse = ApiError & { errors?: FieldError[] }
