import { computed, ref } from 'vue'

const STORAGE_KEY = 'cookie_consent'
// Bump when the banner text or cookie usage changes so visitors are re-asked.
const CONSENT_VERSION = 1
// Danish guidance expects consent to be renewed periodically; 12 months is
// the customary interval.
const MAX_AGE_MS = 365 * 24 * 60 * 60 * 1000

interface StoredConsent {
  version: number
  timestamp: number
  /** Optional cookies: third-party functional widgets (currently the Tawk.to chat). */
  functional: boolean
}

function readStored(): StoredConsent | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as StoredConsent
    if (parsed.version !== CONSENT_VERSION) return null
    if (Date.now() - parsed.timestamp > MAX_AGE_MS) return null
    return parsed
  } catch {
    return null
  }
}

const stored = ref<StoredConsent | null>(readStored())
const settingsOpen = ref(false)

export function useCookieConsent() {
  const hasDecided = computed(() => stored.value !== null)
  const functionalAllowed = computed(() => stored.value?.functional ?? false)

  function save(functional: boolean) {
    const value: StoredConsent = {
      version: CONSENT_VERSION,
      timestamp: Date.now(),
      functional,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    stored.value = value
    settingsOpen.value = false
  }

  return {
    hasDecided,
    functionalAllowed,
    settingsOpen,
    acceptAll: () => save(true),
    declineOptional: () => save(false),
    openSettings: () => {
      settingsOpen.value = true
    },
  }
}
