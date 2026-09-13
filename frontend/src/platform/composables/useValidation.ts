import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Rule } from './useRules'

type Schema<K extends string> = Record<K, Rule[]>

export function useValidation<K extends string>(
  input: Schema<K> | ((form: Record<string, string>) => Schema<K>),
) {
  const { locale } = useI18n()
  const form = reactive<Record<string, string>>({})
  const errors = reactive<Record<string, string>>({})

  const schema = (typeof input === 'function' ? input(form) : input) as Record<string, Rule[]>

  for (const key in schema) {
    form[key] = ''
    errors[key] = ''
  }

  function _runField(key: string): string {
    for (const rule of schema[key]) {
      const result = rule(form[key])
      if (result !== true) return result
    }
    return ''
  }

  function validate(): boolean {
    let valid = true
    for (const key in schema) {
      errors[key] = _runField(key)
      if (errors[key]) valid = false
    }
    return valid
  }

  function clearErrors() {
    for (const key in schema) errors[key] = ''
  }

  watch(locale, () => {
    for (const key in schema) {
      if (errors[key]) errors[key] = _runField(key)
    }
  })

  return {
    form: form as Record<K, string>,
    errors: errors as Record<K, string>,
    validate,
    clearErrors,
  }
}
