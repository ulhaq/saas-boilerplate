import { createI18n } from 'vue-i18n'
import foundationEn from '@/foundation/locales/en'
import foundationDa from '@/foundation/locales/da'
import type { MessageTree } from '@/foundation/module'
import { modules } from '@/products'

/** Deep-merge module messages into the foundation tree (objects merge, leaves/arrays replace). */
function mergeMessages<T extends MessageTree>(base: T, extra: MessageTree): T {
  const out: MessageTree = { ...base }
  for (const [key, value] of Object.entries(extra)) {
    const current = out[key]
    const bothObjects =
      current !== null &&
      typeof current === 'object' &&
      !Array.isArray(current) &&
      value !== null &&
      typeof value === 'object' &&
      !Array.isArray(value)
    out[key] = bothObjects ? mergeMessages(current as MessageTree, value as MessageTree) : value
  }
  return out as T
}

const messages = {
  da: modules.reduce((tree, module) => mergeMessages(tree, module.messages.da), foundationDa),
  en: modules.reduce((tree, module) => mergeMessages(tree, module.messages.en), foundationEn),
}

export type SupportedLocale = keyof typeof messages
export const DEFAULT_LOCALE: SupportedLocale = 'da'
export const LOCALE_ORDER: SupportedLocale[] = ['da', 'en']
export const LOCALE_LABELS: Record<SupportedLocale, string> = {
  da: 'Dansk',
  en: 'English',
}

/** `value` if the app has messages for it, otherwise the default locale. */
export function toSupportedLocale(value: string | null | undefined): SupportedLocale {
  return LOCALE_ORDER.find((locale) => locale === value) ?? DEFAULT_LOCALE
}

// The visitor's last choice; a signed-in user's profile language replaces it
// once the session loads.
const savedLocale = toSupportedLocale(globalThis.localStorage?.getItem('locale'))

export const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: DEFAULT_LOCALE,
  globalInjection: true,
  messages,
})
