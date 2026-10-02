/**
 * Presenters for the in-app notifications the backend writes alongside billing
 * emails (`notify_subscription_managers`): type `billing.<email template>`,
 * payload = the email's data (dates as ISO strings). Imported once from
 * `src/main.ts`.
 */
import { registerNotificationPresenter } from '@/platform/composables/useNotificationPresenter'
import { i18n } from '@/plugins/i18n'

// Email template -> locale key under `notifications.billing`.
const BILLING_NOTIFICATIONS: Record<string, string> = {
  'payment-failed': 'paymentFailed',
  'payment-uncollectible': 'paymentUncollectible',
  'payment-action-required': 'paymentActionRequired',
  'trial-available': 'trialAvailable',
  'trial-ending': 'trialEnding',
  'trial-ended': 'trialEnded',
  'subscription-paused': 'subscriptionPaused',
  'subscription-resumed': 'subscriptionResumed',
  'duplicate-subscription-refunded': 'duplicateSubscriptionRefunded',
}

export const BILLING_NOTIFICATION_TYPES = Object.keys(BILLING_NOTIFICATIONS).map(
  (template) => `billing.${template}`,
)

type Payload = { trial_end_date?: string; trial_days?: number }

function formatDate(value: string | undefined): string | null {
  const date = value ? new Date(value) : null
  if (!date || Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat(i18n.global.locale.value, { dateStyle: 'long' }).format(date)
}

for (const [template, key] of Object.entries(BILLING_NOTIFICATIONS)) {
  registerNotificationPresenter(`billing.${template}`, {
    getTitle: (_payload, t) => t(`notifications.billing.${key}.title`),
    getDescription: (payload, t) => {
      const { trial_end_date, trial_days } = (payload ?? {}) as Payload
      const date = formatDate(trial_end_date)
      // The trial end date can be unknown ("soon"); fall back to undated copy.
      if (key === 'trialEnding' && !date) {
        return t('notifications.billing.trialEnding.descriptionSoon')
      }
      return t(`notifications.billing.${key}.description`, { date, days: trial_days })
    },
    getRoute: () => '/settings/billing',
  })
}
