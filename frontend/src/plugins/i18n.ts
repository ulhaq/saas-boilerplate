import { createI18n } from 'vue-i18n'
import platformEn from '@/platform/locales/en'
import platformDa from '@/platform/locales/da'
import productEn from '@/example/locales/en'
import productDa from '@/example/locales/da'

type MessageTree = Record<string, unknown>

/** Deep-merge product messages into the platform tree (objects merge, leaves/arrays replace). */
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
  da: mergeMessages(platformDa, productDa),
  en: mergeMessages(platformEn, productEn),
}

export type SupportedLocale = keyof typeof messages
export const DEFAULT_LOCALE: SupportedLocale = 'da'
export const LOCALE_ORDER: SupportedLocale[] = ['da', 'en']
export const LOCALE_LABELS: Record<SupportedLocale, string> = {
  da: 'Dansk',
  en: 'English',
}

// `localStorage` doesn't exist during the SSG build, so the prerendered HTML is
// always emitted in the default locale. A visitor who has picked the other
// language sees it swap in once the app hydrates.
const savedLocale = (globalThis.localStorage?.getItem('locale') ??
  DEFAULT_LOCALE) as SupportedLocale

export const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: DEFAULT_LOCALE,
  globalInjection: true,
  messages,
})
