export interface PaginatedResponse<T> {
  items: T[]
  page_number: number
  page_size: number
  total: number
}

export interface PageQueryParams {
  page_number: number
  page_size: number
  sort?: string
  q?: string
  [key: string]: string | number | undefined
}

export interface FilterExpression {
  [field: string]: {
    v: (string | number | boolean)[]
    op: FilterOp
  }
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

export interface ApiError {
  time: string
  path: string
  method: string
  error_code: string
  msg: string
}

export interface FieldError {
  error_code: string
  msg: string
  field: string[]
  ctx?: Record<string, unknown>
}

export interface ApiErrorResponse extends ApiError {
  errors?: FieldError[]
}
