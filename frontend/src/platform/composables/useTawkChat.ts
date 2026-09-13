import { watch } from 'vue'
import { useCookieConsent } from '@/platform/composables/useCookieConsent'

declare global {
  interface Window {
    Tawk_API?: Record<string, unknown>
    Tawk_LoadStart?: Date
  }
}

let injected = false

// Tawk sets its cookies as soon as the embed script loads (verified 2026-06;
// its in-widget consent form does not prevent this), so the script may only
// be injected after the visitor has accepted optional cookies in the banner.
export function useTawkChat() {
  const tawkKey = import.meta.env.VITE_TAWK_KEY as string | undefined
  const { functionalAllowed } = useCookieConsent()

  watch(
    functionalAllowed,
    (allowed) => {
      if (!allowed || injected || !tawkKey) return
      injected = true

      window.Tawk_API = window.Tawk_API ?? {}
      window.Tawk_LoadStart = new Date()

      const script = document.createElement('script')
      script.async = true
      script.src = `https://embed.tawk.to/${tawkKey}`
      script.setAttribute('charset', 'UTF-8')
      script.setAttribute('crossorigin', '*')
      document.head.appendChild(script)
    },
    { immediate: true },
  )
}
