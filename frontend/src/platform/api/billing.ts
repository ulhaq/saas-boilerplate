import { apiClient } from './client'
import type {
  PlanOut,
  SubscriptionOut,
  CheckoutOut,
  CustomerPortalOut,
  UsageOut,
} from '@/platform/types'

export const billingApi = {
  // Plans
  listPlans() {
    return apiClient.get<PlanOut[]>('/billing/plans')
  },

  getPlan(id: number) {
    return apiClient.get<PlanOut>(`/billing/plans/${id}`)
  },

  // Subscriptions
  startTrial(data: { plan_price_id: number }) {
    return apiClient.post<CheckoutOut>('/billing/subscriptions/trial', data)
  },

  checkout(data: { plan_price_id: number }) {
    return apiClient.post<CheckoutOut>('/billing/subscriptions/checkout', data)
  },

  getCurrentSubscription() {
    return apiClient.get<SubscriptionOut>('/billing/subscriptions/current')
  },

  cancelSubscription() {
    return apiClient.post<SubscriptionOut>('/billing/subscriptions/current/cancel')
  },

  resumeSubscription() {
    return apiClient.post<SubscriptionOut>('/billing/subscriptions/current/resume')
  },

  switchPlan(data: { plan_price_id: number }) {
    return apiClient.post<SubscriptionOut>('/billing/subscriptions/current/switch-plan', data)
  },

  updateBillingEmail(data: { billing_email: string }) {
    return apiClient.put<SubscriptionOut>('/billing/subscriptions/current', data)
  },

  getPortalUrl() {
    return apiClient.get<CustomerPortalOut>('/billing/subscriptions/portal')
  },

  getUsage() {
    return apiClient.get<UsageOut>('/billing/usage')
  },
}
