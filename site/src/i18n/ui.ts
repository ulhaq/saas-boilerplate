import { SITE } from '../config'
import type { Locale } from './routes'

const N = SITE.name

const en = {
  htmlLang: 'en',
  switchLanguage: 'Dansk',
  skipToContent: 'Skip to content',
  meta: {
    home: {
      title: `${N} - One place for your team's work`,
      description: `${N} gives your team one place to organise projects, collaborate and get work done.`,
    },
    features: {
      title: `Features - ${N}`,
      description: `Projects, team collaboration, role-based access, API and audit log - see what ${N} includes.`,
    },
    pricing: {
      title: `Pricing - ${N}`,
      description: 'Simple, transparent pricing. Start free and upgrade as your team grows.',
    },
    about: { title: `About ${N}`, description: `Who builds ${N} and why.` },
    contact: {
      title: `Contact ${N}`,
      description: `Get in touch with the ${N} team - questions about the product, pricing, or your account.`,
    },
    privacy: {
      title: `Privacy Policy - ${N}`,
      description: `How ${N} collects, uses and protects personal data under the GDPR.`,
    },
    terms: {
      title: `Terms of Service - ${N}`,
      description: `The terms that apply when you use ${N}.`,
    },
    notFound: { title: `Page not found - ${N}`, description: 'This page does not exist.' },
  },
  nav: {
    features: 'Features',
    pricing: 'Pricing',
    about: 'About',
    contact: 'Contact',
    privacy: 'Privacy policy',
    terms: 'Terms of service',
    login: 'Log in',
    signup: 'Start free',
    waitlist: 'Join the waitlist',
    menu: 'Menu',
  },
  cta: {
    trial: 'Start your {days}-day free trial',
    free: 'Create a free account',
    noCard: 'No credit card required',
    cancel: 'Cancel anytime',
  },
  waitlist: {
    badge: 'Launching soon',
    title: 'Be the first to know',
    sub: `${N} is launching soon. Join the waitlist for early access.`,
    name: 'Name (optional)',
    namePlaceholder: 'Your name',
    email: 'Work email',
    emailPlaceholder: 'you@company.com',
    submit: 'Join the waitlist',
    success: "You're on the list. We'll be in touch.",
  },
  home: {
    kicker: 'For teams who would rather be working',
    headline: 'Your team’s work, <em>in one quiet place.</em>',
    lede: `${N} gives your team one place to organise projects, collaborate and get work done - without juggling tools that don’t talk to each other.`,
    secondaryCta: 'See pricing',
    labels: { how: 'How it works', features: 'Features', pricing: 'Pricing', faq: 'FAQ' },
    howTitle: 'Up and running in three steps.',
    steps: [
      { title: 'Create an account', desc: 'Sign up in seconds - no credit card required.' },
      { title: 'Add your projects', desc: 'Set up projects and invite the people you work with.' },
      {
        title: 'Get going',
        desc: 'Work together with roles, notifications and a full audit trail.',
      },
    ],
    featuresTitle: 'Everything your team needs.',
    featuresSub: `${N} comes with the essentials built in, so you can focus on your work.`,
    featuresLink: 'Read about every feature',
    pricingTitle: 'Simple, transparent pricing.',
    pricingSub: 'Start free. Upgrade when you need more.',
    pricingLink: 'Compare all plans',
    faqTitle: 'Questions, answered.',
    closingTitle: 'Get started <em>today.</em>',
  },
  highlights: [
    { label: 'Setup', value: 'Under a minute' },
    { label: 'Access', value: 'Role-based' },
    { label: 'Data', value: 'Hosted in the EU' },
    { label: 'Languages', value: 'English · Danish' },
  ],
  features: {
    kicker: 'Features',
    title: 'Everything you need, <em>nothing you don’t.</em>',
    lede: `${N} combines the tools your team needs in one simple workspace.`,
    list: [
      {
        key: 'projects',
        title: 'Projects',
        desc: 'Organise work into projects your whole team can see.',
      },
      {
        key: 'teams',
        title: 'Team collaboration',
        desc: 'Invite colleagues and work together in one place.',
      },
      {
        key: 'rbac',
        title: 'Role-based access',
        desc: 'Fine-grained permissions so everyone sees exactly what they should.',
      },
      { key: 'billing', title: 'Flexible plans', desc: 'Start free and upgrade when you need more.' },
      {
        key: 'notifications',
        title: 'Notifications',
        desc: 'Email and in-app updates when it matters.',
      },
      {
        key: 'api',
        title: 'API access',
        desc: 'Integrate with your own systems through the REST API.',
      },
      {
        key: 'audit',
        title: 'Audit log',
        desc: 'A full history of actions taken in your organization.',
      },
      { key: 'i18n', title: 'Multi-language', desc: 'Available in English and Danish.' },
    ],
    trustTitle: 'Built with care for your data',
    trust: [
      { title: 'Hosted in the EU', desc: 'Your data lives on EU-located infrastructure.' },
      {
        title: 'GDPR by default',
        desc: 'Export or erase your data at any time, with automatic retention.',
      },
      { title: 'Encrypted in transit', desc: 'Every connection is protected with TLS.' },
    ],
  },
  pricing: {
    kicker: 'Pricing',
    title: 'Simple, <em>transparent</em> pricing.',
    lede: 'Start free and upgrade as your team grows. No lock-in, no hidden fees.',
    perMonth: 'per month',
    free: 'Free forever',
    exclVat: 'excl. VAT',
    recommended: 'Most popular',
    compareTitle: 'Full comparison',
    feature: 'Feature',
    included: 'Included',
    notIncluded: 'Not included',
    customText: 'Don’t see a plan that fits your needs?',
    customLink: 'Talk to us',
    faqTitle: 'Pricing questions',
  },
  faq: [
    {
      q: `What is ${N}?`,
      a: `${N} is a workspace for teams to organise projects and collaborate.`,
    },
    {
      q: 'Can I add my team?',
      a: 'Yes. Invite colleagues and assign roles. The number of users depends on your plan.',
    },
    {
      q: 'How does the free trial work?',
      a: 'Paid plans come with a free trial - no credit card required. When the trial ends your organization moves to the free plan unless you add a payment method.',
      pricing: true,
    },
    {
      q: 'Can I change or cancel my plan anytime?',
      a: 'Yes. Upgrade, downgrade or cancel at any time from your billing settings.',
      pricing: true,
    },
    {
      q: 'Is there an API?',
      a: 'Yes. Paid plans include API tokens you can use to integrate with your own systems.',
    },
    {
      q: 'Is my data secure and GDPR compliant?',
      a: 'Yes. We process only the data needed to run the service, apply automatic data retention, and never sell your data. See our privacy policy for details.',
    },
  ],
  about: {
    kicker: 'About',
    title: 'We build simple tools that help teams <em>get work done.</em>',
    missionTitle: 'Our mission',
    missionQuote: 'Teams lose time juggling tools that don’t talk to each other.',
    missionBody: `${N} brings the essentials together so you can focus on the work that matters.`,
    valuesTitle: 'What we stand for',
    values: [
      { title: 'Built for people', desc: 'Simple, clear and pleasant to use every day.' },
      { title: 'Security and GDPR', desc: 'We only process the data we need and never sell it.' },
      { title: 'Fast to start', desc: 'No complex setup - sign up and you are up and running.' },
    ],
    contactTitle: 'Have questions?',
    contactSub: 'We are happy to help. Get in touch and we will get back to you.',
    contactLink: 'Write to us',
  },
  contact: {
    kicker: 'Contact',
    title: 'Have a question? <em>We’re happy to help.</em>',
    emailLabel: 'Email',
    responseTime: 'We reply within 2 business days.',
    companyLabel: 'Company',
    form: {
      name: 'Your name',
      namePlaceholder: 'Jane Doe',
      email: 'Your email',
      emailPlaceholder: 'you@company.com',
      subject: 'Subject',
      subjectPlaceholder: 'What is this about?',
      message: 'Message',
      messagePlaceholder: 'Tell us how we can help.',
      submit: 'Send message',
      sending: 'Sending…',
      sentTitle: 'Thanks for reaching out.',
      sentBody: "We'll get back to you within 2 business days.",
    },
  },
  legal: {
    lastUpdated: 'Last updated',
  },
  forms: {
    error: 'Something went wrong. Please try again, or email us directly.',
    rateLimited: 'Too many attempts. Please wait a minute and try again.',
  },
  footer: {
    tagline: 'One place for your team to organise projects and get work done.',
    product: 'Product',
    company: 'Company',
    legal: 'Legal',
    register: 'Create account',
    apiDocs: 'API docs',
    rights: 'All rights reserved.',
  },
  notFound: {
    kicker: 'Error 404',
    title: 'This page <em>has gone missing.</em>',
    lede: 'The page you were looking for does not exist or has moved.',
    home: 'Back to the front page',
  },
}

export type Messages = typeof en

const da: Messages = {
  htmlLang: 'da',
  switchLanguage: 'English',
  skipToContent: 'Spring til indhold',
  meta: {
    home: {
      title: `${N} - Ét sted til dit teams arbejde`,
      description: `${N} giver dit team ét sted at organisere projekter, samarbejde og få tingene gjort.`,
    },
    features: {
      title: `Funktioner - ${N}`,
      description: `Projekter, samarbejde, rollebaseret adgang, API og revisionslog - se hvad ${N} indeholder.`,
    },
    pricing: {
      title: `Priser - ${N}`,
      description: 'Enkle og gennemskuelige priser. Start gratis og opgradér, når teamet vokser.',
    },
    about: { title: `Om ${N}`, description: `Hvem der bygger ${N}, og hvorfor.` },
    contact: {
      title: `Kontakt ${N}`,
      description: `Kom i kontakt med ${N}-teamet - spørgsmål om produktet, priser eller din konto.`,
    },
    privacy: {
      title: `Privatlivspolitik - ${N}`,
      description: `Hvordan ${N} indsamler, bruger og beskytter personoplysninger efter GDPR.`,
    },
    terms: {
      title: `Handelsbetingelser - ${N}`,
      description: `De betingelser der gælder, når du bruger ${N}.`,
    },
    notFound: { title: `Siden findes ikke - ${N}`, description: 'Denne side findes ikke.' },
  },
  nav: {
    features: 'Funktioner',
    pricing: 'Priser',
    about: 'Om os',
    contact: 'Kontakt',
    privacy: 'Privatlivspolitik',
    terms: 'Handelsbetingelser',
    login: 'Log ind',
    signup: 'Start gratis',
    waitlist: 'Skriv dig på ventelisten',
    menu: 'Menu',
  },
  cta: {
    trial: 'Start din gratis prøveperiode på {days} dage',
    free: 'Opret en gratis konto',
    noCard: 'Intet kreditkort krævet',
    cancel: 'Opsig når som helst',
  },
  waitlist: {
    badge: 'Lanceres snart',
    title: 'Vær den første der ved det',
    sub: `${N} lanceres snart. Skriv dig på ventelisten for tidlig adgang.`,
    name: 'Navn (valgfrit)',
    namePlaceholder: 'Dit navn',
    email: 'Arbejdsemail',
    emailPlaceholder: 'dig@virksomhed.dk',
    submit: 'Skriv dig på ventelisten',
    success: 'Du er på listen. Vi vender tilbage.',
  },
  home: {
    kicker: 'Til teams, der hellere vil arbejde',
    headline: 'Dit teams arbejde, <em>samlet ét roligt sted.</em>',
    lede: `${N} giver dit team ét sted at organisere projekter, samarbejde og få tingene gjort - uden at jonglere med værktøjer, der ikke taler sammen.`,
    secondaryCta: 'Se priser',
    labels: { how: 'Sådan virker det', features: 'Funktioner', pricing: 'Priser', faq: 'FAQ' },
    howTitle: 'Kom i gang i tre trin.',
    steps: [
      { title: 'Opret en konto', desc: 'Tilmeld dig på få sekunder - intet kreditkort krævet.' },
      {
        title: 'Tilføj dine projekter',
        desc: 'Opret projekter og invitér dem, du arbejder sammen med.',
      },
      {
        title: 'Kom i gang',
        desc: 'Arbejd sammen med roller, notifikationer og en fuld revisionslog.',
      },
    ],
    featuresTitle: 'Alt hvad dit team har brug for.',
    featuresSub: `${N} har det vigtigste indbygget, så du kan fokusere på dit arbejde.`,
    featuresLink: 'Læs om alle funktioner',
    pricingTitle: 'Enkle og gennemskuelige priser.',
    pricingSub: 'Start gratis. Opgradér når du har brug for mere.',
    pricingLink: 'Sammenlign alle planer',
    faqTitle: 'Spørgsmål og svar.',
    closingTitle: 'Kom i gang <em>i dag.</em>',
  },
  highlights: [
    { label: 'Opsætning', value: 'Under et minut' },
    { label: 'Adgang', value: 'Rollebaseret' },
    { label: 'Data', value: 'Hostet i EU' },
    { label: 'Sprog', value: 'Dansk · engelsk' },
  ],
  features: {
    kicker: 'Funktioner',
    title: 'Alt hvad du har brug for, <em>intet du ikke har.</em>',
    lede: `${N} samler de værktøjer, dit team har brug for, i ét enkelt arbejdsområde.`,
    list: [
      {
        key: 'projects',
        title: 'Projekter',
        desc: 'Organisér arbejdet i projekter, hele teamet kan se.',
      },
      { key: 'teams', title: 'Samarbejde', desc: 'Invitér kolleger og arbejd sammen ét sted.' },
      {
        key: 'rbac',
        title: 'Rollebaseret adgang',
        desc: 'Detaljerede tilladelser, så alle ser præcis det, de skal.',
      },
      {
        key: 'billing',
        title: 'Fleksible planer',
        desc: 'Start gratis og opgradér, når du har brug for mere.',
      },
      {
        key: 'notifications',
        title: 'Notifikationer',
        desc: 'Email og beskeder i appen, når det betyder noget.',
      },
      { key: 'api', title: 'API-adgang', desc: 'Integrér med jeres egne systemer via REST API.' },
      {
        key: 'audit',
        title: 'Revisionslog',
        desc: 'En komplet historik over handlinger i din organisation.',
      },
      { key: 'i18n', title: 'Flere sprog', desc: 'Tilgængelig på dansk og engelsk.' },
    ],
    trustTitle: 'Bygget med omtanke for dine data',
    trust: [
      { title: 'Hostet i EU', desc: 'Dine data ligger på infrastruktur placeret i EU.' },
      {
        title: 'GDPR som standard',
        desc: 'Eksportér eller slet dine data når som helst, med automatisk sletning.',
      },
      { title: 'Krypteret forbindelse', desc: 'Al trafik er beskyttet med TLS.' },
    ],
  },
  pricing: {
    kicker: 'Priser',
    title: 'Enkle og <em>gennemskuelige</em> priser.',
    lede: 'Start gratis og opgradér, når teamet vokser. Ingen binding, ingen skjulte gebyrer.',
    perMonth: 'pr. måned',
    free: 'Gratis for altid',
    exclVat: 'ekskl. moms',
    recommended: 'Mest populær',
    compareTitle: 'Fuld sammenligning',
    feature: 'Funktion',
    included: 'Inkluderet',
    notIncluded: 'Ikke inkluderet',
    customText: 'Finder du ikke en plan, der passer?',
    customLink: 'Tal med os',
    faqTitle: 'Spørgsmål om priser',
  },
  faq: [
    {
      q: `Hvad er ${N}?`,
      a: `${N} er et arbejdsområde, hvor teams kan organisere projekter og samarbejde.`,
    },
    {
      q: 'Kan jeg tilføje mit team?',
      a: 'Ja. Invitér kolleger og tildel roller. Antallet af brugere afhænger af din plan.',
    },
    {
      q: 'Hvordan fungerer den gratis prøveperiode?',
      a: 'Betalte planer har en gratis prøveperiode - intet kreditkort krævet. Når prøveperioden slutter, flyttes organisationen til den gratis plan, medmindre du tilføjer en betalingsmetode.',
      pricing: true,
    },
    {
      q: 'Kan jeg ændre eller opsige min plan når som helst?',
      a: 'Ja. Du kan opgradere, nedgradere eller opsige når som helst under faktureringsindstillinger.',
      pricing: true,
    },
    {
      q: 'Er der et API?',
      a: 'Ja. Betalte planer inkluderer API-tokens, som du kan bruge til at integrere med jeres egne systemer.',
    },
    {
      q: 'Er mine data sikre og GDPR-kompatible?',
      a: 'Ja. Vi behandler kun de data, der er nødvendige for at drive tjenesten, sletter data automatisk efter faste regler og sælger aldrig dine data. Se vores privatlivspolitik for detaljer.',
    },
  ],
  about: {
    kicker: 'Om os',
    title: 'Vi bygger enkle værktøjer, der hjælper teams med at <em>få tingene gjort.</em>',
    missionTitle: 'Vores mission',
    missionQuote: 'Teams spilder tid på værktøjer, der ikke taler sammen.',
    missionBody: `${N} samler det vigtigste, så I kan fokusere på det arbejde, der betyder noget.`,
    valuesTitle: 'Det står vi for',
    values: [
      { title: 'Bygget til mennesker', desc: 'Enkelt, overskueligt og rart at bruge hver dag.' },
      {
        title: 'Sikkerhed og GDPR',
        desc: 'Vi behandler kun de data, vi har brug for, og sælger dem aldrig.',
      },
      { title: 'Hurtigt i gang', desc: 'Ingen kompliceret opsætning - tilmeld dig, og du er klar.' },
    ],
    contactTitle: 'Har du spørgsmål?',
    contactSub: 'Vi hjælper gerne. Kontakt os, så vender vi tilbage.',
    contactLink: 'Skriv til os',
  },
  contact: {
    kicker: 'Kontakt',
    title: 'Har du et spørgsmål? <em>Vi hjælper gerne.</em>',
    emailLabel: 'Email',
    responseTime: 'Vi svarer inden for 2 hverdage.',
    companyLabel: 'Virksomhed',
    form: {
      name: 'Dit navn',
      namePlaceholder: 'Jens Jensen',
      email: 'Din email',
      emailPlaceholder: 'dig@virksomhed.dk',
      subject: 'Emne',
      subjectPlaceholder: 'Hvad drejer det sig om?',
      message: 'Besked',
      messagePlaceholder: 'Fortæl os, hvordan vi kan hjælpe.',
      submit: 'Send besked',
      sending: 'Sender…',
      sentTitle: 'Tak for din besked.',
      sentBody: 'Vi vender tilbage inden for 2 hverdage.',
    },
  },
  legal: {
    lastUpdated: 'Senest opdateret',
  },
  forms: {
    error: 'Noget gik galt. Prøv igen, eller skriv direkte til os.',
    rateLimited: 'For mange forsøg. Vent et minut, og prøv igen.',
  },
  footer: {
    tagline: 'Ét sted, hvor dit team kan organisere projekter og få tingene gjort.',
    product: 'Produkt',
    company: 'Virksomhed',
    legal: 'Juridisk',
    register: 'Opret konto',
    apiDocs: 'API-dokumentation',
    rights: 'Alle rettigheder forbeholdes.',
  },
  notFound: {
    kicker: 'Fejl 404',
    title: 'Denne side <em>er forsvundet.</em>',
    lede: 'Siden, du ledte efter, findes ikke eller er flyttet.',
    home: 'Tilbage til forsiden',
  },
}

const MESSAGES: Record<Locale, Messages> = { en, da }

export function useMessages(locale: Locale): Messages {
  return MESSAGES[locale]
}

/** `fmt('Choose {plan}', { plan: 'Pro' })` */
export function fmt(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? `{${key}}`))
}
