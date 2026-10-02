import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { expect, test, vi } from 'vitest'
import AuditLog from '@/platform/pages/settings/audit-log.vue'
import { auditActionValues } from '@/api-schema'
import { i18n } from '@/plugins/i18n'
import { useAuditLogsStore } from '@/platform/stores/auditLogs'

test('the action filter offers every action an organization can have', async () => {
  setActivePinia(createPinia())
  const store = useAuditLogsStore()
  store.list = vi.fn(async () => ({ items: [], page_number: 1, page_size: 20, total: 0 }))
  const wrapper = mount(AuditLog, { global: { plugins: [i18n] }, attachTo: document.body })
  await flushPromises()

  // Open the select the way a keyboard user would.
  await wrapper.find('[role="combobox"]').trigger('keydown', { key: 'Enter' })
  await flushPromises()
  const options = [...document.querySelectorAll('[role="option"]')].map((o) =>
    o.textContent?.trim(),
  )

  // Every backend action except those recorded without an organization,
  // sorted, after the "all actions" entry.
  const organizationLess = ['auth.password_reset', 'user.email_change', 'billing.webhook']
  expect(options.slice(1)).toEqual(
    auditActionValues.filter((a) => !organizationLess.includes(a)).sort(),
  )
  expect(options).toContain('billing.duplicate_subscription_refunded')
  expect(options).not.toContain('user.email_change')
  wrapper.unmount()
})
