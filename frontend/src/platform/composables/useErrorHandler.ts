import type { AxiosError } from 'axios'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/platform/composables/useToast'
import type { ApiErrorResponse, FieldError } from '@/platform/types/api'

function toAxiosError(err: unknown): AxiosError<ApiErrorResponse> | null {
  const e = err as AxiosError<ApiErrorResponse>
  return e?.isAxiosError && e.response?.data ? e : null
}

export function useErrorHandler() {
  const { t, te } = useI18n()
  const { toast } = useToast()

  function resolveField(field: string[]): string {
    const key = `errors.fields.${field.join('__')}`
    return te(key) ? t(key) : (field[field.length - 1] ?? 'field')
  }

  function resolveFieldError(fe: FieldError): string {
    const fieldLabel = resolveField(fe.field)
    const apiKey = `errors.api.${fe.error_code}`
    return te(apiKey) ? t(apiKey, { field: fieldLabel, msg: fe.msg, ...fe.ctx }) : fe.msg
  }

  /** Translate the first/most relevant error to a display string. */
  function resolveError(err: unknown, fallback?: string): string {
    const axiosErr = toAxiosError(err)
    if (!axiosErr) return fallback ?? t('errors.common')

    const data = axiosErr.response!.data

    // Pydantic errors array - surface the first one
    if (Array.isArray(data.errors) && data.errors.length > 0) {
      return resolveFieldError(data.errors[0]!)
    }

    // Flat error with error_code
    if (data.error_code) {
      const apiKey = `errors.api.${data.error_code}`
      if (te(apiKey)) return t(apiKey)
      if (data.msg) return data.msg
    }

    // error_code missing but API still sent a human-readable message
    if (data.msg) return data.msg

    return fallback ?? t('errors.common')
  }

  /**
   * Resolve ALL validation field errors to a map keyed by field path.
   * e.g. { 'body__email': 'Email is too short' }
   * Use in forms to map server errors back to specific inputs.
   */
  function resolveFieldErrors(err: unknown): Record<string, string> {
    const axiosErr = toAxiosError(err)
    if (!axiosErr) return {}
    const data = axiosErr.response!.data
    if (!Array.isArray(data.errors)) return {}

    const result: Record<string, string> = {}
    for (const fe of data.errors) {
      result[fe.field.join('__')] = resolveFieldError(fe)
    }
    return result
  }

  function isPlanFeatureError(err: unknown): boolean {
    return toAxiosError(err)?.response?.data?.error_code === 'plan_feature_unavailable'
  }

  /** Show a destructive toast with the translated error. */
  function handleError(err: unknown, fallback?: string): void {
    if (isPlanFeatureError(err)) return
    toast({ title: resolveError(err, fallback), variant: 'destructive' })
  }

  return { handleError, resolveError, resolveFieldErrors, isPlanFeatureError }
}
