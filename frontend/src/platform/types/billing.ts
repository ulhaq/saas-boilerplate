export interface PlanPriceOut {
  id: number
  plan_id: number
  amount: number
  currency: string
  interval: 'month' | 'year'
  interval_count: number
  trial_period_days: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PlanSettingOut {
  key: string
  value: number | null
}

export interface PlanOut {
  id: number
  name: string
  description: string | null
  is_active: boolean
  prices: PlanPriceOut[]
  plan_settings: PlanSettingOut[]
  created_at: string
  updated_at: string
}

export interface SubscriptionOut {
  id: number
  organization_id: number
  plan_price_id: number | null
  status: 'incomplete' | 'active' | 'trialing' | 'past_due' | 'canceled' | 'paused'
  current_period_start: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  canceled_at: string | null
  cancel_at: string | null
  trial_end: string | null
  plan_price: PlanPriceOut | null
  billing_email: string | null
  has_payment_method: boolean
  trial_used: boolean
  features: string[]
  plan_settings: PlanSettingOut[]
  created_at: string
  updated_at: string
}

export interface UsageItemOut {
  metric: string
  count: number
  limit: number | null
}

export interface UsageOut {
  period_start: string
  usage: UsageItemOut[]
}

export interface CheckoutOut {
  checkout_url: string
}

export interface CustomerPortalOut {
  portal_url: string
}
