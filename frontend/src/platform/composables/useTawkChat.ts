declare global {
  interface Window {
    Tawk_API?: Record<string, unknown>
    Tawk_LoadStart?: Date
  }
}

let injected = false

// Loaded only inside the signed-in app (DashboardLayout); the embed script is
// injected once per page load and skipped when VITE_TAWK_KEY is unset.
export function useTawkChat() {
  const tawkKey = import.meta.env.VITE_TAWK_KEY as string | undefined
  if (injected || !tawkKey) return
  injected = true

  window.Tawk_API = window.Tawk_API ?? {}
  window.Tawk_LoadStart = new Date()

  const script = document.createElement('script')
  script.async = true
  script.src = `https://embed.tawk.to/${tawkKey}`
  script.setAttribute('charset', 'UTF-8')
  script.setAttribute('crossorigin', '*')
  document.head.appendChild(script)
}
