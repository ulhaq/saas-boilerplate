import type { Schema } from './api'

// Narrowed beyond the API: the backend declares these as plain strings.
export type BillingInterval = 'month' | 'year'
export type SubscriptionStatus =
  | 'incomplete'
  | 'active'
  | 'trialing'
  | 'past_due'
  | 'canceled'
  | 'paused'

export type PlanPriceOut = Omit<Schema<'PlanPriceOut'>, 'interval'> & {
  interval: BillingInterval
}
export type PlanSettingOut = Schema<'PlanSettingOut'>
export type PlanOut = Omit<Schema<'PlanOut'>, 'prices'> & { prices: PlanPriceOut[] }
export type SubscriptionOut = Omit<Schema<'SubscriptionOut'>, 'status' | 'plan_price'> & {
  status: SubscriptionStatus
  plan_price: PlanPriceOut | null
}
export type UsageItemOut = Schema<'UsageItemOut'>
export type UsageOut = Schema<'UsageOut'>
export type CheckoutOut = Schema<'CheckoutOut'>
export type CustomerPortalOut = Schema<'CustomerPortalOut'>
