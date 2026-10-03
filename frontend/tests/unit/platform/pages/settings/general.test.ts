import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import General from '@/platform/pages/settings/general.vue'
import { i18n } from '@/plugins/i18n'
import { OWNER_ROLE_NAME } from '@/platform/constants'
import { useAuthStore } from '@/platform/stores/auth'
import { useOrganizationsStore } from '@/platform/stores/organizations'
import { useProfileStore } from '@/platform/stores/profile'
import { useSessionStore } from '@/platform/stores/session'
import { useUsersStore } from '@/platform/stores/users'
import type { OrganizationOut, RoleOut, UserOut } from '@/platform/types'

const t = i18n.global.t

const confirm = vi.fn(async (..._args: unknown[]) => true)
const toast = vi.fn()
const push = vi.fn()
vi.mock('@/platform/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))
vi.mock('@/platform/composables/useToast', () => ({ useToast: () => ({ toast }) }))
vi.mock('vue-router', async (importOriginal) => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push }),
  onBeforeRouteLeave: vi.fn(),
}))

const ORG: OrganizationOut = {
  id: 1,
  name: 'Acme',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: null,
}

function role(name: string, permissions: string[], isProtected = false): RoleOut {
  return {
    id: name.length,
    name,
    description: null,
    organization_id: ORG.id,
    is_protected: isProtected,
    permissions: permissions.map((p, i) => ({ id: i + 1, name: p, description: null })),
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
  }
}

function user(id: number, name: string, roles: RoleOut[] = []): UserOut {
  return {
    id,
    name,
    email: `${name.toLowerCase().replace(' ', '.')}@acme.dk`,
    locale: 'en',
    theme: 'system',
    terms_accepted_at: null,
    mfa_enabled: false,
    roles,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
  }
}

const MEMBERS = [user(2, 'Grace Hopper'), user(3, 'Alan Turing')]

let orgs: ReturnType<typeof useOrganizationsStore>
let users: ReturnType<typeof useUsersStore>
let auth: ReturnType<typeof useAuthStore>
let wrapper: VueWrapper
const mounted: VueWrapper[] = []

/** Mount the page for a signed-in user with these permissions in organization ``ORG``. */
async function mountGeneral(permissions: string[], { owner = false } = {}): Promise<VueWrapper> {
  setActivePinia(createPinia())
  const roles = [role('Custom', permissions)]
  if (owner) roles.push(role(OWNER_ROLE_NAME, [], true))
  const profile = useProfileStore()
  profile.user = user(1, 'Ada Lovelace', roles)
  profile.permissions = permissions
  profile.fetchMe = vi.fn(async () => {})
  // The active organization comes from the access token's `oid` claim.
  useSessionStore().accessToken = `h.${btoa(JSON.stringify({ oid: ORG.id }))}.s`

  orgs = useOrganizationsStore()
  orgs.organizations = [ORG]
  orgs.fetchOrganizations = vi.fn(async () => {})
  orgs.getUsers = vi.fn(async () => ({
    items: MEMBERS,
    page_number: 1,
    page_size: 20,
    total: MEMBERS.length,
  }))
  orgs.patch = vi.fn(async (_id: number, data) => ({ ...ORG, ...data }))
  orgs.remove = vi.fn(async () => {})
  users = useUsersStore()
  users.removeFromOrganization = vi.fn(async () => {})
  auth = useAuthStore()
  auth.logout = vi.fn(async () => {})

  wrapper = mount(General, { global: { plugins: [i18n] }, attachTo: document.body })
  mounted.push(wrapper)
  await flushPromises()
  return wrapper
}

const button = (label: string) => wrapper.findAll('button').find((b) => b.text().trim() === label)

async function click(label: string) {
  const el = button(label)
  expect(el, `button "${label}"`).toBeDefined()
  await el!.trigger('click')
  await flushPromises()
}

const memberNames = () => wrapper.findAll('p.font-medium.text-sm').map((p) => p.text())

beforeEach(() => {
  i18n.global.locale.value = 'en'
  confirm.mockReset().mockResolvedValue(true)
  toast.mockClear()
  push.mockClear()
})

afterEach(() => {
  // Some tests mount the page twice (once per user).
  mounted.splice(0).forEach((w) => w.unmount())
  document.body.innerHTML = ''
})

describe('general settings page', () => {
  test('a member without permissions sees only the organization header', async () => {
    await mountGeneral([])

    expect(wrapper.text()).toContain(`${t('settings.organizationId')}: ${ORG.id}`)
    expect(wrapper.text()).not.toContain(t('settings.organizationDetails'))
    expect(wrapper.text()).not.toContain(t('settings.members'))
    expect(wrapper.text()).not.toContain(t('settings.dangerZone'))
    expect(orgs.getUsers).not.toHaveBeenCalled()
  })

  test('renames the organization once the name has changed', async () => {
    await mountGeneral(['update:organization'])
    const input = wrapper.find('form input')
    expect((input.element as HTMLInputElement).value).toBe(ORG.name)
    const save = () => button(t('common.saveChanges'))!
    expect(save().attributes('disabled')).toBeDefined()

    await input.setValue('  Acme Corp ')
    expect(save().attributes('disabled')).toBeUndefined()
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(orgs.patch).toHaveBeenCalledWith(ORG.id, { name: 'Acme Corp' })
    // The switcher and topbar read the cached list.
    expect(orgs.fetchOrganizations).toHaveBeenCalled()
  })

  test('an empty name is rejected without calling the API', async () => {
    await mountGeneral(['update:organization'])
    await wrapper.find('form input').setValue('   ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(orgs.patch).not.toHaveBeenCalled()
  })

  test('lists members, and only managers can remove them after confirming', async () => {
    await mountGeneral(['read:user'])
    expect(orgs.getUsers).toHaveBeenCalledWith(ORG.id)
    expect(memberNames()).toEqual(['Grace Hopper', 'Alan Turing'])
    expect(wrapper.text()).toContain('GH')
    expect(wrapper.findAll('button.text-destructive')).toHaveLength(0)

    await mountGeneral(['read:user', 'manage:organization_user'])
    const remove = () => wrapper.findAll('button.text-destructive')
    expect(remove()).toHaveLength(2)

    confirm.mockResolvedValueOnce(false)
    await remove()[1]!.trigger('click')
    await flushPromises()
    expect(users.removeFromOrganization).not.toHaveBeenCalled()

    await remove()[1]!.trigger('click')
    await flushPromises()
    expect(users.removeFromOrganization).toHaveBeenCalledWith(3)
    expect(memberNames()).toEqual(['Grace Hopper'])
    expect(toast).toHaveBeenCalledWith({ title: t('organizations.usersDialog.userRemoved') })
  })

  test('only the owner sees the danger zone', async () => {
    await mountGeneral(['update:organization', 'read:user'])
    expect(wrapper.text()).not.toContain(t('settings.dangerZone'))

    await mountGeneral([], { owner: true })
    expect(wrapper.text()).toContain(t('settings.dangerZone'))
  })

  test('deleting the organization needs its exact name and a confirmation, then signs out', async () => {
    await mountGeneral([], { owner: true })
    await click(t('settings.deleteOrganization'))
    const submit = () => wrapper.find('form button[type="submit"]')
    const nameInput = wrapper.find('#delete-org-name')

    await nameInput.setValue('acme')
    expect(submit().attributes('disabled')).toBeDefined()
    await nameInput.setValue('Acme')
    expect(submit().attributes('disabled')).toBeUndefined()

    confirm.mockResolvedValueOnce(false)
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(orgs.remove).not.toHaveBeenCalled()

    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(orgs.remove).toHaveBeenCalledWith(ORG.id)
    expect(auth.logout).toHaveBeenCalled()
    expect(push).toHaveBeenCalledWith('/login')
  })

  test('a failed delete keeps the user here and shows the error', async () => {
    await mountGeneral([], { owner: true })
    orgs.remove = vi.fn(async () => {
      throw { isAxiosError: true, response: { data: { msg: 'Cannot delete right now' } } }
    })
    await click(t('settings.deleteOrganization'))
    await wrapper.find('#delete-org-name').setValue('Acme')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Cannot delete right now')
    expect(auth.logout).not.toHaveBeenCalled()
    expect(push).not.toHaveBeenCalled()
  })
})
