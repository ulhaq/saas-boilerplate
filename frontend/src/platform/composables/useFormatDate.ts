import { onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

export function useFormatDate() {
  const { locale, t } = useI18n()
  const now = ref(Date.now())

  const timer = setInterval(() => {
    now.value = Date.now()
  }, 10_000)

  onUnmounted(() => clearInterval(timer))

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString(locale.value, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  function formatDateTime(iso: string): string {
    return new Date(iso).toLocaleString(locale.value, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  function formatRelativeTime(iso: string): string {
    const diff = (new Date(iso).getTime() - now.value) / 1000
    const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })
    const abs = Math.abs(diff)
    if (abs < 10) return t('common.justNow')
    if (abs < 60) return t('common.lessThanAMinuteAgo')
    if (abs < 3600) return rtf.format(Math.round(diff / 60), 'minute')
    if (abs < 86400) return rtf.format(Math.round(diff / 3600), 'hour')
    if (abs < 2592000) return rtf.format(Math.round(diff / 86400), 'day')
    return rtf.format(Math.round(diff / 2592000), 'month')
  }

  return { formatDate, formatDateTime, formatRelativeTime }
}
