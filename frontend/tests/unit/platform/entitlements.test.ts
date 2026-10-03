import { expect, test } from 'vitest'
import { provideEntitlements, useEntitlements, type Entitlements } from '@/platform/entitlements'

test('without a plan module every feature is on and nothing is limited', async () => {
  const entitlements = useEntitlements()

  expect(entitlements.hasFeature('api_token')).toBe(true)
  expect(entitlements.limitFor('seats')).toBeNull()
  expect(entitlements.planSummary()).toBeNull()
  await expect(entitlements.load()).resolves.toBeUndefined()
})

test('a module provides the entitlements, once', () => {
  const plan: Entitlements = {
    hasFeature: (feature) => feature === 'api_token',
    limitFor: () => 3,
    load: async () => {},
    loadLimits: async () => {},
    clear: () => {},
    planSummary: () => null,
  }
  provideEntitlements(() => plan)

  expect(useEntitlements().hasFeature('sso')).toBe(false)
  expect(useEntitlements().limitFor('seats')).toBe(3)
  expect(() => provideEntitlements(() => plan)).toThrow(/already provides/)
})
