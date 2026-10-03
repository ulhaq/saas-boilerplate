import { onBeforeRouteLeave } from 'vue-router'
import { useI18n } from 'vue-i18n'

export function useFormGuard(isDirty: () => boolean) {
  const { t } = useI18n()

  onBeforeRouteLeave(() => {
    if (isDirty()) {
      return window.confirm(t('common.unsavedChangesWarning'))
    }
  })
}
