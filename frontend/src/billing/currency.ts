/**
 * The currency the user picked for the plans, remembered in this browser. Picked
 * on the billing page, or on the marketing site, whose links into the app carry
 * it as `?currency=` (`adoptCurrencyFromUrl`, run once at startup).
 */
const STORAGE_KEY = 'billing.currency'
const QUERY_PARAM = 'currency'
const CURRENCY_CODE = /^[a-z]{3}$/

export function rememberedCurrency(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function rememberCurrency(currency: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, currency)
  } catch {
    // Storage blocked: the choice lasts until the page is left.
  }
}

/** Remember a `?currency=` the app was opened with, and drop it from the address. Runs
 * before the router starts, so it never sees the parameter. A currency no plan is priced
 * in is ignored by the billing page. */
export function adoptCurrencyFromUrl(location: Location = window.location): void {
  const url = new URL(location.href)
  const currency = url.searchParams.get(QUERY_PARAM)?.trim().toLowerCase()
  if (currency === undefined) return
  if (CURRENCY_CODE.test(currency)) rememberCurrency(currency)
  url.searchParams.delete(QUERY_PARAM)
  window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash)
}
