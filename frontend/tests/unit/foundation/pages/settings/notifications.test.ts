import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import Notifications from '@/foundation/pages/settings/notifications.vue'
import { i18n } from '@/plugins/i18n'
import { useNotificationsStore } from '@/foundation/stores/notifications'
import type { NotificationPreferenceOut } from '@/foundation/types/notification'

const t = i18n.global.t

vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  onBeforeRouteLeave: vi.fn(),
}))

// Test-local categories (no module copy): rows are labelled by their key.
const PREFERENCES: NotificationPreferenceOut[] = [
  { category: 'test.news', in_app: true, email: true, email_required: false },
  { category: 'test.critical', in_app: true, email: true, email_required: true },
]

let store: ReturnType<typeof useNotificationsStore>

async function mountPage(preferences = PREFERENCES): Promise<VueWrapper> {
  setActivePinia(createPinia())
  store = useNotificationsStore()
  store.fetchPreferences = vi.fn(async () => {
    store.preferences = preferences.map((p) => ({ ...p }))
  })
  store.updatePreferences = vi.fn(async () => {})
  const wrapper = mount(Notifications, { global: { plugins: [i18n] }, attachTo: document.body })
  await flushPromises()
  return wrapper
}

const checkbox = (wrapper: VueWrapper, category: string, channel: 'inApp' | 'email') =>
  wrapper.get(`[aria-label="${category}: ${t(`notificationPreferences.${channel}`)}"]`)

const saveButton = (wrapper: VueWrapper) =>
  wrapper.findAll('button').find((b) => b.text().includes(t('common.saveChanges')))!

let wrapper: VueWrapper | undefined

beforeEach(() => {
  i18n.global.locale.value = 'en'
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  document.body.innerHTML = ''
})

describe('Notification settings page', () => {
  test('shows each category with its channels, a required email locked on', async () => {
    wrapper = await mountPage()

    expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    expect(checkbox(wrapper, 'test.news', 'email').attributes('data-state')).toBe('checked')
    expect(checkbox(wrapper, 'test.news', 'email').attributes('disabled')).toBeUndefined()
    expect(checkbox(wrapper, 'test.critical', 'email').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain(t('notificationPreferences.emailRequired'))
    expect(saveButton(wrapper).attributes('disabled')).toBeDefined()
  })

  test('saves only the categories that changed', async () => {
    wrapper = await mountPage()

    await checkbox(wrapper, 'test.news', 'email').trigger('click')
    expect(saveButton(wrapper).attributes('disabled')).toBeUndefined()
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(store.updatePreferences).toHaveBeenCalledWith([
      { category: 'test.news', in_app: true, email: false },
    ])
  })

  test('says so when there is nothing to configure', async () => {
    wrapper = await mountPage([])

    expect(wrapper.text()).toContain(t('notificationPreferences.emptyTitle'))
    expect(wrapper.find('form').exists()).toBe(false)
  })
})
