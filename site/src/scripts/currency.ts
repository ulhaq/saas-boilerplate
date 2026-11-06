/**
 * The plan currency and billing period the visitor picked on the pricing cards,
 * remembered in the browser and handed to the app: every link into it (`a[href]`
 * under the app's origin, read from `body[data-app-url]`) gets `?currency=<code>`
 * and `?interval=<month|year>`, which the app's billing page then offers. Nothing
 * is added for a choice not yet made.
 */
const KEY = 'currency'
const INTERVAL_KEY = 'interval'

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Not remembered: it still applies on this page and its links.
  }
}

export function savedCurrency(): string | null {
  return read(KEY)
}

export function saveCurrency(currency: string): void {
  write(KEY, currency)
  tagAppLinks(currency)
}

export function savedInterval(): string | null {
  return read(INTERVAL_KEY)
}

export function saveInterval(interval: string): void {
  write(INTERVAL_KEY, interval)
  tagAppLinks(undefined, interval)
}

export function tagAppLinks(
  currency: string | null = savedCurrency(),
  interval: string | null = savedInterval(),
): void {
  const app = document.body.dataset.appUrl
  if (!app || (!currency && !interval)) return
  const origin = new URL(app, window.location.href).origin
  document.querySelectorAll<HTMLAnchorElement>('a[href]').forEach((link) => {
    const url = new URL(link.href)
    if (url.origin !== origin) return
    if (currency) url.searchParams.set('currency', currency.toLowerCase())
    if (interval) url.searchParams.set('interval', interval)
    link.href = url.href
  })
}
