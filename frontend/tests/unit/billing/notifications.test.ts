import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { describe, expect, test } from 'vitest'
import { BILLING_NOTIFICATION_TYPES, registerBillingNotifications } from '@/billing/notifications'
import { useNotificationPresenter } from '@/platform/composables/useNotificationPresenter'
import { i18n, type SupportedLocale } from '@/plugins/i18n'
import type { NotificationOut } from '@/platform/types/notification'

registerBillingNotifications()

function notification(type: string, payload: Record<string, unknown> = {}): NotificationOut {
  return {
    id: 1,
    notification_type: type,
    payload,
    read_at: null,
    created_at: '2026-10-01T00:00:00Z',
  } as NotificationOut
}

/** Present a notification the way the bell and the notifications page do. */
function present(n: NotificationOut, locale: SupportedLocale) {
  i18n.global.locale.value = locale
  let result = { title: '', description: null as string | null, route: null as string | null }
  mount(
    defineComponent({
      setup() {
        const { getTitle, getDescription, getRoute } = useNotificationPresenter()
        result = { title: getTitle(n), description: getDescription(n), route: getRoute(n) }
        return () => null
      },
    }),
    { global: { plugins: [i18n] } },
  )
  return result
}

describe('billing notifications', () => {
  test.each(
    BILLING_NOTIFICATION_TYPES.flatMap((type) => [
      [type, 'en'],
      [type, 'da'],
    ]),
  )('%s has its own %s title and description and links to billing', (type, locale) => {
    const fallbackTitle = i18n.global.t('notifications.title')
    const { title, description, route } = present(
      notification(type, { trial_end_date: '2026-10-15', trial_days: 14 }),
      locale as SupportedLocale,
    )

    expect(title).not.toBe(fallbackTitle)
    expect(title).not.toContain('notifications.billing')
    expect(description).toBeTruthy()
    expect(description).not.toContain('notifications.billing')
    expect(route).toBe('/settings/billing')
  })

  test('a trial ending notification shows the date in the reader’s language', () => {
    const n = notification('billing.trial-ending', { trial_end_date: '2026-10-15' })
    expect(present(n, 'en').description).toBe('Your trial ends on October 15, 2026.')
    expect(present(n, 'da').description).toContain('15. oktober 2026')
  })

  test('an unknown trial end date falls back to undated copy', () => {
    const n = notification('billing.trial-ending', { trial_end_date: 'soon' })
    expect(present(n, 'en').description).toBe('Your trial ends soon.')
  })
})
