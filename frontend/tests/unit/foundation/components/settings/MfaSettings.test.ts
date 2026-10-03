import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import MfaSettings from '@/foundation/components/settings/MfaSettings.vue'
import OtpInput from '@/foundation/components/common/OtpInput.vue'
import { i18n } from '@/plugins/i18n'
import { useMfaStore } from '@/foundation/stores/mfa'
import { useProfileStore } from '@/foundation/stores/profile'
import type { UserOut } from '@/foundation/types'

const t = i18n.global.t

const toast = vi.fn()
vi.mock('@/foundation/composables/useToast', () => ({ useToast: () => ({ toast }) }))
vi.mock('qrcode', () => ({ toDataURL: vi.fn(async (uri: string) => `data:qr,${uri}`) }))

const CODES = ['aaaaa-11111', 'bbbbb-22222']
const SETUP = {
  secret: 'JBSWY3DPEHPK3PXP',
  otpauth_uri: 'otpauth://totp/x?secret=JBSWY3DPEHPK3PXP',
}

function user(mfaEnabled: boolean): UserOut {
  return {
    id: 1,
    name: 'Ada',
    email: 'ada@example.org',
    locale: 'en',
    theme: 'system',
    terms_accepted_at: null,
    mfa_enabled: mfaEnabled,
    roles: [],
    created_at: '2026-01-01T00:00:00Z',
    updated_at: null,
  }
}

const apiError = (error_code: string) => ({
  isAxiosError: true,
  response: { data: { error_code } },
})

let mfa: ReturnType<typeof useMfaStore>
let wrapper: VueWrapper

async function mountMfa(mfaEnabled: boolean) {
  setActivePinia(createPinia())
  const profile = useProfileStore()
  profile.user = user(mfaEnabled)
  mfa = useMfaStore()
  // The real actions keep profile.user.mfa_enabled in sync; so do these.
  mfa.setup = vi.fn(async () => SETUP)
  mfa.enable = vi.fn(async () => {
    profile.user!.mfa_enabled = true
    return CODES
  })
  mfa.disable = vi.fn(async () => {
    profile.user!.mfa_enabled = false
  })
  mfa.regenerateRecoveryCodes = vi.fn(async () => CODES)
  wrapper = mount(MfaSettings, { global: { plugins: [i18n] }, attachTo: document.body })
  await flushPromises()
}

// Dialogs render in a portal on <body>, so look everything up in the document.
const button = (label: string) =>
  [...document.querySelectorAll('button')].find((b) => b.textContent?.trim() === label)

async function click(label: string) {
  const el = button(label)
  expect(el, `button "${label}"`).toBeDefined()
  el!.click()
  await flushPromises()
}

/** The OTP input currently on screen (the card's, or the open dialog's). */
const otp = () => wrapper.findAllComponents(OtpInput).slice(-1)[0]!

async function enterCode(code: string) {
  otp().vm.$emit('update:modelValue', code)
  otp().vm.$emit('complete', code)
  await flushPromises()
}

async function typeInto(selector: string, value: string) {
  const input = document.querySelector<HTMLInputElement>(selector)!
  expect(input, selector).not.toBeNull()
  input.value = value
  input.dispatchEvent(new Event('input'))
  await flushPromises()
}

const recoveryCodesShown = () =>
  [...document.querySelectorAll('[role="dialog"] li')].map((li) => li.textContent?.trim())

beforeEach(() => {
  i18n.global.locale.value = 'en'
  toast.mockClear()
})

afterEach(() => {
  wrapper.unmount()
  document.body.innerHTML = ''
})

describe('MFA settings', () => {
  test('enrolls: scan the QR code, confirm a code, then see the recovery codes once', async () => {
    await mountMfa(false)
    expect(wrapper.text()).not.toContain(t('settings.mfa.enabled'))

    await click(t('settings.mfa.enable'))
    expect(mfa.setup).toHaveBeenCalledOnce()
    expect(wrapper.find('img').attributes('src')).toBe(`data:qr,${SETUP.otpauth_uri}`)
    expect(wrapper.text()).toContain(SETUP.secret)

    // A complete code submits on its own.
    await enterCode('123456')
    expect(mfa.enable).toHaveBeenCalledWith('123456')
    expect(toast).toHaveBeenCalledWith({ title: t('settings.mfa.enabledToast') })
    expect(recoveryCodesShown()).toEqual(CODES)
    expect(wrapper.text()).toContain(t('settings.mfa.enabled'))
    expect(wrapper.text()).toContain(t('settings.mfa.regenerateCodes'))
  })

  test('a wrong enrollment code is reported and cleared, and setup can be cancelled', async () => {
    await mountMfa(false)
    mfa.enable = vi.fn(async () => {
      throw apiError('mfa_code_invalid')
    })
    await click(t('settings.mfa.enable'))

    await enterCode('000000')
    expect(wrapper.text()).toContain(t('errors.api.mfa_code_invalid'))
    expect(otp().props('modelValue')).toBe('')
    expect(recoveryCodesShown()).toEqual([])

    await click(t('common.cancel'))
    expect(wrapper.find('img').exists()).toBe(false)
    expect(button(t('settings.mfa.enable'))).toBeDefined()
  })

  test('disabling needs the password and a code, and submits once both are in', async () => {
    await mountMfa(true)
    await click(t('settings.mfa.disable'))
    const submit = () =>
      [...document.querySelectorAll<HTMLButtonElement>('[role="dialog"] button[type="submit"]')][0]!

    // A complete code without the password does not submit.
    await enterCode('123456')
    expect(mfa.disable).not.toHaveBeenCalled()
    expect(submit().disabled).toBe(true)

    await typeInto('#mfa-disable-password', 'hunter2')
    expect(submit().disabled).toBe(false)
    submit().click()
    await flushPromises()

    expect(mfa.disable).toHaveBeenCalledWith({ password: 'hunter2', code: '123456' })
    expect(toast).toHaveBeenCalledWith({ title: t('settings.mfa.disabledToast') })
    expect(button(t('settings.mfa.enable'))).toBeDefined()
  })

  test('disabling with a wrong password says so', async () => {
    await mountMfa(true)
    mfa.disable = vi.fn(async () => {
      throw apiError('login_failed')
    })
    await click(t('settings.mfa.disable'))
    await typeInto('#mfa-disable-password', 'wrong')
    await enterCode('123456')

    expect(mfa.disable).toHaveBeenCalledOnce()
    expect(document.body.textContent).toContain(t('settings.incorrectCurrentPassword'))
    expect(otp().props('modelValue')).toBe('')
  })

  test('disabling can use a recovery code instead of the authenticator', async () => {
    await mountMfa(true)
    await click(t('settings.mfa.disable'))
    await click(t('auth.mfaUseRecoveryCode'))

    await typeInto('#mfa-disable-password', 'hunter2')
    await typeInto('#mfa-disable-code', 'aaaaa-11111')
    const submit = document.querySelector<HTMLButtonElement>(
      '[role="dialog"] button[type="submit"]',
    )!
    submit.click()
    await flushPromises()

    expect(mfa.disable).toHaveBeenCalledWith({ password: 'hunter2', code: 'aaaaa-11111' })
  })

  test('regenerating recovery codes takes a code and shows the new set', async () => {
    await mountMfa(true)
    await click(t('settings.mfa.regenerateCodes'))
    await enterCode('654321')

    expect(mfa.regenerateRecoveryCodes).toHaveBeenCalledWith('654321')
    expect(recoveryCodesShown()).toEqual(CODES)
  })
})
