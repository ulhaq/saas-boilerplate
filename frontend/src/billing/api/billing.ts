import { api } from '@/foundation/api/client'

export const billingApi = {
  // Plans
  listPlans() {
    return api.get('/billing/plans')
  },

  getPlan(id: number) {
    return api.get('/billing/plans/{plan_id}', { path: { plan_id: id } })
  },

  // Subscriptions
  startTrial(data: { plan_price_id: number }) {
    return api.post('/billing/subscriptions/trial', { body: data })
  },

  checkout(data: { plan_price_id: number }) {
    return api.post('/billing/subscriptions/checkout', { body: data })
  },

  getCurrentSubscription() {
    return api.get('/billing/subscriptions/current')
  },

  cancelSubscription() {
    return api.post('/billing/subscriptions/current/cancel')
  },

  resumeSubscription() {
    return api.post('/billing/subscriptions/current/resume')
  },

  switchPlan(data: { plan_price_id: number }) {
    return api.post('/billing/subscriptions/current/switch-plan', { body: data })
  },

  updateBillingEmail(data: { billing_email: string }) {
    return api.patch('/billing/subscriptions/current', { body: data })
  },

  getPortalUrl() {
    return api.get('/billing/subscriptions/portal')
  },

  getUsage() {
    return api.get('/billing/usage')
  },
}
