import { useSubscriptionStore } from '@/platform/stores/subscription'

export function usePlanFeature() {
  const subscriptionStore = useSubscriptionStore()

  function hasFeature(feature: string): boolean {
    return subscriptionStore.hasFeature(feature)
  }

  return { hasFeature }
}
