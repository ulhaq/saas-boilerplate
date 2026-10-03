export default {
  nav: {
    subscription: 'Subscription',
  },
  common: {
    exclVat: 'excl. VAT',
  },
  notifications: {
    billing: {
      paymentFailed: {
        title: 'Payment failed',
        description:
          "We couldn't collect your latest payment. Update your payment method to keep your subscription.",
      },
      paymentUncollectible: {
        title: 'Subscription downgraded',
        description: "We couldn't collect payment, so your organization is now on the free plan.",
      },
      paymentActionRequired: {
        title: 'Payment needs your action',
        description: 'Your bank asked for extra verification. Complete it to finish the payment.',
      },
      trialAvailable: {
        title: 'Your free trial is waiting',
        description: 'Try the paid features free for {days} days.',
      },
      trialEnding: {
        title: 'Your trial ends soon',
        description: 'Your trial ends on {date}.',
        descriptionSoon: 'Your trial ends soon.',
      },
      trialEnded: {
        title: 'Your trial has ended',
        description: 'Your organization is back on the free plan.',
      },
      subscriptionPaused: {
        title: 'Subscription paused',
        description: 'Add a payment method to resume your subscription.',
      },
      subscriptionResumed: {
        title: 'Subscription resumed',
        description: 'Your subscription is active again.',
      },
      duplicateSubscriptionRefunded: {
        title: 'Duplicate subscription refunded',
        description: 'We canceled a second subscription and refunded it in full.',
      },
    },
  },
  notificationPreferences: {
    categories: {
      billing: {
        trial: {
          title: 'Free trial',
          description: 'When a trial is available, about to end, or has ended.',
        },
        payment: {
          title: 'Payment problems',
          description: 'Failed payments and payments that need your action.',
        },
        subscription: {
          title: 'Subscription changes',
          description: 'When the subscription is paused, resumed or refunded.',
        },
      },
    },
  },
  subscription: {
    title: 'Subscription',
    description: 'Manage your subscription',
    currentPlan: 'Current plan',
    unknownPlan: 'Unknown plan',
    noSubscription: 'No active subscription',
    choosePlan: 'Choose a plan below to get started.',
    availablePlans: 'Available plans',
    noPlansAvailable: 'No plans are currently available.',
    noPricesAvailable: 'No pricing options available.',
    subscribe: 'Subscribe',
    free: 'Free',
    startTrialTitle: 'Start your free trial',
    heroTrialSubtitle: 'Start with {days} days free, then {price} / {interval}',
    startTrialDays: '{days}-day free trial',
    startTrialButton: 'Start {days}-day free trial',
    noCardRequired: 'No credit card required',
    startSubscriptionTitle: 'Complete your subscription',
    trialEndsIn: 'Your free trial ends on {date}. Add a payment method to avoid interruption.',
    trialEndsAllSet:
      "Your free trial ends on {date}. You're all set - your subscription will activate automatically.",
    addPaymentMethod: 'Add payment method',
    updatePaymentMethod: 'Update payment method',
    trialEndedTitle: 'Your trial has ended',
    trialEndedDescription:
      'Your {plan} subscription is paused. Add a payment method to resume access.',
    manageBilling: 'Manage billing',
    manageBillingTooltip:
      'Update your payment method, download invoices, and manage billing details.',
    billingEmailTitle: 'Billing email',
    billingEmailDescription: 'Invoices and receipts are sent to this email.',
    billingEmailLabel: 'Billing email',
    billingEmailPlaceholder: "billing{'@'}company.com",
    billingEmailSave: 'Save',
    cancelSubscription: 'Cancel subscription',
    resumeSubscription: 'Resume subscription',
    renewsOn: 'Renews on {date}',
    cancelScheduled: 'Cancels on {date}',
    cancelPending: "Your subscription cancels on {date}. You'll move to the free plan.",
    cancelTitle: 'Cancel subscription?',
    cancelDescription: 'Your subscription will remain active until the end of the current period.',
    cancelConfirm: 'Cancel subscription',
    cancelScheduledSuccess: 'Subscription will be cancelled at end of current period',
    resumed: 'Subscription resumed',
    upgrade: 'Upgrade',
    downgrade: 'Downgrade',
    switchPlanTitle: 'Switch plan?',
    switchPlanDescription:
      'Your subscription will be updated immediately. Proration will be applied to your next invoice.',
    switchPlanSuccess: 'Subscription plan updated',
    incompleteNotice: 'You have a pending checkout. Cancel it to switch to a different plan.',
    checkoutSuccess: 'Payment successful!',
    checkoutSuccessDescription: 'Your subscription is now active.',
    checkoutPending: 'Still processing your payment\u2026',
    checkoutPendingDescription: 'This may take a moment. Check your subscription page shortly.',
    checkoutCancelled: 'Checkout cancelled',
    checkoutCancelledDescription: 'No changes were made to your subscription.',
    returnToBilling: 'Return to subscription',
    goToDashboard: 'Go to dashboard',
    fetchFailed: 'Failed to load subscription',
    unusedTrialBanner: 'Unlock full access with a free trial - no credit card required.',
    startFreeTrial: 'Start free trial',
    trialEnding: 'Your free trial ends in {time}.',
    paymentFailed:
      'Your last payment failed. Please update your payment method to avoid losing access.',
    status: {
      active: 'Active',
      trialing: 'Trial',
      past_due: 'Past due',
      canceled: 'Canceled',
      incomplete: 'Incomplete',
      paused: 'Paused',
    },
  },
}
