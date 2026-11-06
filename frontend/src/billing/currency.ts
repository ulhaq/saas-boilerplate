/**
 * The currency and billing period the user picked for the plans, remembered in
 * this browser. Picked on the billing page, or on the marketing site, whose links
 * into the app carry them as `?currency=` and `?interval=`
 * (`adoptPlanChoiceFromUrl`, run once at startup).
 */
const STORAGE_KEY = 'billing.currency'
const INTERVAL_STORAGE_KEY = 'billing.interval'
const QUERY_PARAM = 'currency'
const INTERVAL_QUERY_PARAM = 'interval'
const CURRENCY_CODE = /^[a-z]{3}$/
const INTERVALS = ['day', 'week', 'month', 'year']

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
    // Storage blocked: the choice lasts until the page is left.
  }
}

export function rememberedCurrency(): string | null {
  return read(STORAGE_KEY)
}

export function rememberCurrency(currency: string): void {
  write(STORAGE_KEY, currency)
}

export function rememberedInterval(): string | null {
  return read(INTERVAL_STORAGE_KEY)
}

export function rememberInterval(interval: string): void {
  write(INTERVAL_STORAGE_KEY, interval)
}

/** Remember a `?currency=` and `?interval=` the app was opened with, and drop them from
 * the address. Runs before the router starts, so it never sees the parameters. A currency
 * or period no plan is priced in is ignored by the billing page. */
export function adoptPlanChoiceFromUrl(location: Location = window.location): void {
  const url = new URL(location.href)
  const currency = url.searchParams.get(QUERY_PARAM)?.trim().toLowerCase()
  const interval = url.searchParams.get(INTERVAL_QUERY_PARAM)?.trim().toLowerCase()
  if (currency === undefined && interval === undefined) return
  if (currency !== undefined && CURRENCY_CODE.test(currency)) rememberCurrency(currency)
  if (interval !== undefined && INTERVALS.includes(interval)) rememberInterval(interval)
  url.searchParams.delete(QUERY_PARAM)
  url.searchParams.delete(INTERVAL_QUERY_PARAM)
  window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash)
}
