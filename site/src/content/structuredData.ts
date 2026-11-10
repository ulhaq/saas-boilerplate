/**
 * Structured data (schema.org JSON-LD) for search engines and AI assistants,
 * built from the same copy, plans and company details the pages show - so it
 * never says anything a visitor can't read on the page. `Base.astro` renders
 * whatever a view passes as `jsonLd`.
 *
 * - Front page: the organization, the website and the product with its plans.
 * - Pricing: the product with its plans.
 * - Pages with a FAQ (front page, pricing): the questions they show.
 *
 * No ratings or reviews: schema.org markup must reflect real ones.
 */
import { SITE } from '../config'
import { path, type Locale } from '../i18n/routes'
import { useMessages } from '../i18n/ui'
import { CURRENCIES, PLANS } from './plans'

export type JsonLd = Record<string, unknown>

const abs = (href: string, site: URL) => new URL(href, site).href
const orgId = (site: URL) => abs('/#organization', site)
const appId = (site: URL) => abs('/#software', site)

export function organization(site: URL): JsonLd {
  const e = SITE.legalEntity
  return {
    '@type': 'Organization',
    '@id': orgId(site),
    name: SITE.name,
    legalName: e.name,
    vatID: e.registrationNumber,
    url: abs('/', site),
    logo: abs('/logo.png', site),
    email: SITE.supportEmail,
    address: e.address,
  }
}

export function website(locale: Locale, site: URL): JsonLd {
  return {
    '@type': 'WebSite',
    '@id': abs(`${path('home', locale)}#website`, site),
    name: SITE.name,
    url: abs(path('home', locale), site),
    inLanguage: locale,
    publisher: { '@id': orgId(site) },
  }
}

/** The product, offered as one Offer per plan, currency and billing period
 * (the free plan monthly only; the prices exclude VAT, as the pricing page says). */
export function softwareApplication(locale: Locale, site: URL): JsonLd {
  const t = useMessages(locale)
  const pricing = abs(path('pricing', locale), site)
  const offers = PLANS.flatMap((plan) =>
    CURRENCIES.flatMap((currency) =>
      (plan.amount[currency] ? (['P1M', 'P1Y'] as const) : (['P1M'] as const)).map((period) => {
        const price = (period === 'P1M' ? plan.amount[currency] : plan.yearly[currency]) / 100
        return {
          '@type': 'Offer',
          name: plan.name,
          description: plan.description[locale],
          url: pricing,
          price,
          priceCurrency: currency,
          priceSpecification: {
            '@type': 'UnitPriceSpecification',
            price,
            priceCurrency: currency,
            billingDuration: period,
            valueAddedTaxIncluded: false,
          },
        }
      }),
    ),
  )
  return {
    '@type': 'SoftwareApplication',
    '@id': appId(site),
    name: SITE.name,
    description: t.meta.home.description,
    applicationCategory: 'BusinessApplication',
    operatingSystem: 'Web browser',
    url: abs(path('home', locale), site),
    image: abs('/og-image.png', site),
    inLanguage: locale,
    publisher: { '@id': orgId(site) },
    offers,
  }
}

export function faqPage(items: readonly { q: string; a: string }[], url: string): JsonLd {
  return {
    '@type': 'FAQPage',
    '@id': `${url}#faq`,
    mainEntity: items.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  }
}

/** One `<script type="application/ld+json">` body; `<` escaped so copy can't close the tag. */
export function serialize(items: JsonLd[]): string {
  return JSON.stringify({ '@context': 'https://schema.org', '@graph': items }).replace(/</g, '\\u003c')
}
