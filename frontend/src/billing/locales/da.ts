export default {
  nav: {
    subscription: 'Abonnement',
  },
  common: {
    exclVat: 'ekskl. moms',
  },
  notifications: {
    billing: {
      paymentFailed: {
        title: 'Betaling mislykkedes',
        description:
          'Vi kunne ikke opkræve din seneste betaling. Opdater din betalingsmetode for at beholde dit abonnement.',
      },
      paymentUncollectible: {
        title: 'Abonnement nedgraderet',
        description: 'Vi kunne ikke opkræve betalingen, så din organisation er nu på gratisplanen.',
      },
      paymentActionRequired: {
        title: 'Betalingen kræver din handling',
        description:
          'Din bank har bedt om ekstra bekræftelse. Gennemfør den for at fuldføre betalingen.',
      },
      trialAvailable: {
        title: 'Din gratis prøveperiode venter',
        description: 'Prøv de betalte funktioner gratis i {days} dage.',
      },
      trialEnding: {
        title: 'Din prøveperiode slutter snart',
        description: 'Din prøveperiode slutter den {date}.',
        descriptionSoon: 'Din prøveperiode slutter snart.',
      },
      trialEnded: {
        title: 'Din prøveperiode er slut',
        description: 'Din organisation er tilbage på gratisplanen.',
      },
      subscriptionPaused: {
        title: 'Abonnement sat på pause',
        description: 'Tilføj en betalingsmetode for at genoptage dit abonnement.',
      },
      subscriptionResumed: {
        title: 'Abonnement genoptaget',
        description: 'Dit abonnement er aktivt igen.',
      },
      duplicateSubscriptionRefunded: {
        title: 'Dobbelt abonnement refunderet',
        description: 'Vi har annulleret et ekstra abonnement og refunderet det fuldt ud.',
      },
    },
  },
  notificationPreferences: {
    categories: {
      billing: {
        trial: {
          title: 'Gratis prøveperiode',
          description: 'Når en prøveperiode er tilgængelig, snart slutter eller er slut.',
        },
        payment: {
          title: 'Betalingsproblemer',
          description: 'Mislykkede betalinger og betalinger, der kræver din handling.',
        },
        subscription: {
          title: 'Ændringer i abonnementet',
          description: 'Når abonnementet sættes på pause, genoptages eller refunderes.',
        },
      },
    },
  },
  subscription: {
    title: 'Abonnement',
    description: 'Administrer dit abonnement',
    currentPlan: 'Nuværende plan',
    unknownPlan: 'Ukendt plan',
    noSubscription: 'Intet aktivt abonnement',
    choosePlan: 'Vælg en plan nedenfor for at komme i gang.',
    availablePlans: 'Tilgængelige planer',
    noPlansAvailable: 'Ingen planer er tilgængelige i øjeblikket.',
    noPricesAvailable: 'Ingen prisvalgmuligheder tilgængelige.',
    subscribe: 'Abonner',
    free: 'Gratis',
    startTrialTitle: 'Start din gratis prøveperiode',
    heroTrialSubtitle: 'Start med {days} dage gratis, derefter {price} / {interval}',
    startTrialDays: '{days} dages gratis prøveperiode',
    startTrialButton: 'Start {days} dages gratis prøveperiode',
    noCardRequired: 'Intet kreditkort påkrævet',
    startSubscriptionTitle: 'Fuldfør dit abonnement',
    trialEndsIn:
      'Din gratis prøveperiode slutter den {date}. Tilføj en betalingsmetode for at undgå afbrydelse.',
    trialEndsAllSet:
      'Din gratis prøveperiode slutter den {date}. Alt er klar - dit abonnement aktiveres automatisk.',
    addPaymentMethod: 'Tilføj betalingsmetode',
    updatePaymentMethod: 'Opdater betalingsmetode',
    trialEndedTitle: 'Din prøveperiode er slut',
    trialEndedDescription:
      'Dit {plan}-abonnement er sat på pause. Tilføj en betalingsmetode for at genoptage adgangen.',
    manageBilling: 'Administrer fakturering',
    manageBillingTooltip:
      'Opdater din betalingsmetode, download fakturaer og administrer faktureringsoplysninger.',
    billingEmailTitle: 'Faktureringsmail',
    billingEmailDescription: 'Fakturaer og kvitteringer sendes til denne email.',
    billingEmailLabel: 'Faktureringsmail',
    billingEmailPlaceholder: "fakturering{'@'}virksomhed.dk",
    billingEmailSave: 'Gem',
    cancelSubscription: 'Annuller abonnement',
    resumeSubscription: 'Genoptag abonnement',
    renewsOn: 'Fornyes den {date}',
    cancelScheduled: 'Annulleres den {date}',
    cancelPending: 'Dit abonnement annulleres den {date}. Du skifter til gratisplanen.',
    cancelTitle: 'Annuller abonnement?',
    cancelDescription:
      'Dit abonnement forbliver aktivt indtil slutningen af den nuværende periode.',
    cancelConfirm: 'Annuller abonnement',
    cancelScheduledSuccess:
      'Abonnement vil blive annulleret ved slutningen af den nuværende periode',
    resumed: 'Abonnement genoptaget',
    upgrade: 'Opgrader',
    downgrade: 'Nedgrader',
    switchPlanTitle: 'Skift plan?',
    switchPlanDescription:
      'Dit abonnement opdateres med det samme. Proratering vil blive anvendt på din næste faktura.',
    switchPlanSuccess: 'Abonnementsplan opdateret',
    incompleteNotice:
      'Du har en afventende betaling. Annuller den for at skifte til en anden plan.',
    checkoutSuccess: 'Betaling gennemført!',
    checkoutSuccessDescription: 'Dit abonnement er nu aktivt.',
    checkoutPending: 'Behandler din betaling\u2026',
    checkoutPendingDescription: 'Dette kan tage et øjeblik. Tjek din abonnementside snart.',
    checkoutCancelled: 'Betaling annulleret',
    checkoutCancelledDescription: 'Der er ikke foretaget ændringer i dit abonnement.',
    returnToBilling: 'Tilbage til abonnement',
    goToDashboard: 'Gå til dashboard',
    fetchFailed: 'Kunne ikke hente abonnement',
    unusedTrialBanner: 'Få fuld adgang med en gratis prøveperiode - intet kreditkort kræves.',
    startFreeTrial: 'Start gratis prøveperiode',
    trialEnding: 'Din gratis prøveperiode slutter om {time}.',
    paymentFailed:
      'Din seneste betaling mislykkedes. Opdater din betalingsmetode for at undgå at miste adgang.',
    status: {
      active: 'Aktiv',
      trialing: 'Prøveperiode',
      past_due: 'Forfalden',
      canceled: 'Annulleret',
      incomplete: 'Ufuldstændig',
      paused: 'Sat på pause',
    },
  },
}
