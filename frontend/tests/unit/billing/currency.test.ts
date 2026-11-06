import { beforeEach, describe, expect, test } from 'vitest'
import { adoptCurrencyFromUrl, rememberedCurrency } from '@/billing/currency'

function openAt(path: string) {
  window.history.replaceState(null, '', path)
  adoptCurrencyFromUrl()
}

const address = () => window.location.pathname + window.location.search + window.location.hash

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState(null, '', '/')
})

describe('adoptCurrencyFromUrl', () => {
  test('remembers the currency from the site and drops it from the address', () => {
    openAt('/register?currency=DKK&utm_source=site#top')

    expect(rememberedCurrency()).toBe('dkk')
    expect(address()).toBe('/register?utm_source=site#top')
  })

  test('ignores a value that is no currency code, still dropping it', () => {
    openAt('/register?currency=<script>')

    expect(rememberedCurrency()).toBeNull()
    expect(address()).toBe('/register')
  })

  test('leaves the address and an earlier choice alone without the parameter', () => {
    localStorage.setItem('billing.currency', 'eur')
    openAt('/login?next=%2Fnotes')

    expect(rememberedCurrency()).toBe('eur')
    expect(address()).toBe('/login?next=%2Fnotes')
  })
})
