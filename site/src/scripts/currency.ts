/**
 * The plan currency the visitor picked on the pricing cards, remembered in the
 * browser and handed to the app: every link into it (`a[href]` under the app's
 * origin, read from `body[data-app-url]`) gets `?currency=<code>`, which the
 * app's billing page then offers. Nothing is added until a currency is picked.
 */
const KEY = 'currency'

export function savedCurrency(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function saveCurrency(currency: string): void {
  try {
    localStorage.setItem(KEY, currency)
  } catch {
    // Not remembered: it still applies on this page and its links.
  }
  tagAppLinks(currency)
}

export function tagAppLinks(currency: string | null = savedCurrency()): void {
  const app = document.body.dataset.appUrl
  if (!app || !currency) return
  const origin = new URL(app, window.location.href).origin
  document.querySelectorAll<HTMLAnchorElement>('a[href]').forEach((link) => {
    const url = new URL(link.href)
    if (url.origin !== origin) return
    url.searchParams.set('currency', currency.toLowerCase())
    link.href = url.href
  })
}
