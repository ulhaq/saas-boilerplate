import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import ApiTokens from '@/platform/pages/settings/api-tokens.vue'
import { i18n } from '@/plugins/i18n'
import { BADGE_MAX, PlanFeature } from '@/platform/constants'
import { useApiTokensStore } from '@/platform/stores/apiTokens'
import { useProfileStore } from '@/platform/stores/profile'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import type { ApiTokenCreate, ApiTokenResponse } from '@/platform/types'

const t = i18n.global.t

const toast = vi.fn()
vi.mock('@/platform/composables/useToast', () => ({ useToast: () => ({ toast }) }))

function token(id: number, overrides: Partial<ApiTokenResponse> = {}): ApiTokenResponse {
  return {
    id,
    name: `Token ${id}`,
    token_prefix: `pre${id}`,
    permissions: ['read:user'],
    created_at: '2026-01-01T00:00:00Z',
    expires_at: null,
    last_used_at: null,
    revoked_at: null,
    is_expired: false,
    ...overrides,
  }
}

const PERMISSIONS = ['read:user', 'read:role', 'manage:api_token']

const mountApiTokens = () =>
  mount(ApiTokens, {
    global: { plugins: [i18n], stubs: { RouterLink: true } },
    attachTo: document.body,
  })

let store: ReturnType<typeof useApiTokensStore>

async function mountPage(
  tokens: ApiTokenResponse[] = [],
  { features = [PlanFeature.API_TOKEN] as string[] } = {},
): Promise<VueWrapper> {
  setActivePinia(createPinia())
  useProfileStore().permissions = PERMISSIONS
  useSubscriptionStore().hasFeature = (f: string) => features.includes(f)
  store = useApiTokensStore()
  store.fetchTokens = vi.fn(async () => {
    store.tokens = tokens
  })
  store.createToken = vi.fn(async (data: ApiTokenCreate) => ({
    ...token(99, { name: data.name, permissions: data.permissions }),
    expires_at: data.expires_at ?? null,
    token: 'sk_secret-value',
  }))
  store.revokeToken = vi.fn(async () => {})
  const wrapper = mountApiTokens()
  await flushPromises()
  return wrapper
}

// Dialogs render in a portal on <body>, so look everything up in the document.
function buttons(label: string): HTMLButtonElement[] {
  return [...document.querySelectorAll('button')].filter((b) => b.textContent?.trim() === label)
}

async function click(el: Element | undefined, what: string) {
  expect(el, what).toBeDefined()
  ;(el as HTMLElement).click()
  await flushPromises()
}

const lastButton = (label: string) => buttons(label).slice(-1)[0]

function permissionRow(perm: string): HTMLElement | undefined {
  return [...document.querySelectorAll<HTMLElement>('[role="dialog"] .cursor-pointer')].find(
    (row) => row.textContent?.trim() === perm,
  )
}

async function typeName(name: string) {
  const input = document.querySelector<HTMLInputElement>('[role="dialog"] input')!
  input.value = name
  input.dispatchEvent(new Event('input'))
  await flushPromises()
}

let wrapper: VueWrapper | undefined

beforeEach(() => {
  i18n.global.locale.value = 'en'
  toast.mockClear()
})

afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  document.body.innerHTML = ''
  vi.restoreAllMocks()
})

describe('API tokens page', () => {
  test('lists tokens by prefix, with expiry and overflowing permissions summarized', async () => {
    const many = ['a:1', 'b:2', 'c:3', 'd:4', 'e:5', 'f:6']
    wrapper = await mountPage([
      token(1, { permissions: many }),
      token(2, { is_expired: true, expires_at: '2026-02-01T00:00:00Z' }),
    ])

    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('sk_pre1...')
    expect(rows[0]!.text()).toContain(t('settings.tokenNeverExpires'))
    expect(rows[0]!.text()).toContain(t('settings.tokenNeverUsed'))
    for (const perm of many.slice(0, BADGE_MAX)) expect(rows[0]!.text()).toContain(perm)
    expect(rows[0]!.text()).not.toContain(many[BADGE_MAX])
    expect(rows[0]!.text()).toContain(`+${many.length - BADGE_MAX}`)

    expect(rows[1]!.text()).toContain(t('settings.tokenExpired'))
    expect(rows[1]!.classes()).toContain('opacity-60')
  })

  test('creates a token with the chosen permissions and shows its secret once', async () => {
    wrapper = await mountPage()
    await click(buttons(t('settings.createToken'))[0], 'open create dialog')

    // Only the caller's own permissions can be delegated.
    for (const perm of PERMISSIONS) expect(permissionRow(perm), perm).toBeDefined()

    const submit = () => lastButton(t('settings.createToken'))!
    expect(submit().disabled).toBe(true)
    await typeName('  CI deploy  ')
    expect(submit().disabled).toBe(true) // still no permission
    await click(permissionRow('read:role'), 'pick read:role')
    await click(permissionRow('read:user'), 'pick read:user')
    await click(permissionRow('read:role'), 'unpick read:role')
    expect(submit().disabled).toBe(false)

    await click(submit(), 'submit')
    expect(store.createToken).toHaveBeenCalledWith({
      name: 'CI deploy',
      permissions: ['read:user'],
      expires_at: null,
    })
    expect(document.body.textContent).toContain(t('settings.copyTokenWarning'))
    expect(document.querySelector('code')?.textContent?.trim()).toBe('sk_secret-value')
    expect(toast).toHaveBeenCalledWith({ title: t('settings.tokenCreated') })
  })

  test('a failed create keeps the dialog open and reports the error', async () => {
    wrapper = await mountPage()
    store.createToken = vi.fn(async () => {
      throw new Error('boom')
    })
    await click(buttons(t('settings.createToken'))[0], 'open create dialog')
    await typeName('CI')
    await click(permissionRow('read:user'), 'pick read:user')
    await click(lastButton(t('settings.createToken')), 'submit')

    expect(toast).toHaveBeenCalledWith({
      title: t('settings.failedToCreateToken'),
      variant: 'destructive',
    })
    expect(document.body.textContent).not.toContain(t('settings.copyTokenWarning'))
    expect(document.querySelector('[role="dialog"] input')).not.toBeNull()
  })

  test('revokes a token only after confirmation', async () => {
    wrapper = await mountPage([token(1), token(2)])

    await click(buttons(t('settings.revokeToken'))[1], 'revoke second token')
    expect(store.revokeToken).not.toHaveBeenCalled()
    expect(document.body.textContent).toContain(t('settings.revokeTokenDescription'))

    // The confirm button is last: in the alert dialog, after the table rows.
    await click(lastButton(t('settings.revokeTokenConfirm')), 'confirm revoke')
    expect(store.revokeToken).toHaveBeenCalledWith(2)
    expect(toast).toHaveBeenCalledWith({ title: t('settings.tokenRevoked') })
  })

  test('without the plan feature the page is locked and a plan error is not toasted', async () => {
    wrapper = await mountPage([], { features: [] })
    expect(wrapper.text()).toContain(t('planFeature.unavailableMessage'))
    expect(wrapper.find('[inert]').exists()).toBe(true)

    // The API refuses too: the overlay already explains it, so no error toast.
    const planError = {
      isAxiosError: true,
      response: { data: { error_code: 'plan_feature_unavailable' } },
    }
    store.fetchTokens = vi.fn(async () => {
      throw planError
    })
    wrapper.unmount()
    wrapper = mountApiTokens()
    await flushPromises()
    expect(store.fetchTokens).toHaveBeenCalled()
    expect(toast).not.toHaveBeenCalled()
  })

  test('other load failures are reported', async () => {
    wrapper = await mountPage()
    store.fetchTokens = vi.fn(async () => {
      throw new Error('network')
    })
    wrapper.unmount()
    wrapper = mountApiTokens()
    await flushPromises()
    expect(toast).toHaveBeenCalledWith({
      title: t('settings.failedToLoadTokens'),
      variant: 'destructive',
    })
  })
})
