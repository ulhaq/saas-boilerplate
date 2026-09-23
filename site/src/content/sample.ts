import type { Locale } from '../i18n/routes'

/**
 * Example content for the hero visuals - a typeset impression of the product,
 * not real data. Every theme's `HeroVisual.astro` draws from this, so the
 * story is the same whichever theme is built.
 */
export interface SampleProject {
  name: string
  owner: string
  people: number
  status: string
  /** `done` is struck through or dimmed; `review` gets the warning tint. */
  state: 'active' | 'review' | 'done'
  /** 0-100, for progress bars. */
  progress: number
}

interface Sample {
  title: string
  projects: SampleProject[]
  columns: { project: string; owner: string; people: string; status: string }
  nav: string[]
  kpis: { label: string; value: string }[]
  activeCount: string
  caption: string
  thisWeek: string
  peopleSuffix: string
  note: { title: string; body: string }
  ping: string
  crowd: { value: string; label: string }
}

const SAMPLE: Record<Locale, Sample> = {
  en: {
    title: 'Projects',
    projects: [
      { name: 'Storefront relaunch', owner: 'Maja K.', people: 6, status: 'Active', state: 'active', progress: 72 },
      { name: 'Q3 board report', owner: 'Anders L.', people: 3, status: 'In review', state: 'review', progress: 45 },
      { name: 'Customer onboarding', owner: 'Sofie N.', people: 4, status: 'Active', state: 'active', progress: 88 },
      { name: 'New pricing page', owner: 'Jonas B.', people: 2, status: 'Done', state: 'done', progress: 100 },
    ],
    columns: { project: 'Project', owner: 'Owner', people: 'People', status: 'Status' },
    nav: ['Projects', 'Members', 'Roles', 'Audit log', 'Billing'],
    kpis: [
      { label: 'Active projects', value: '24' },
      { label: 'Members', value: '18' },
      { label: 'Events today', value: '312' },
    ],
    activeCount: '4 active',
    caption: 'Fig. 1 - Your projects, as your team sees them.',
    thisWeek: 'This week',
    peopleSuffix: 'people',
    note: { title: 'Nice work, team!', body: 'New pricing page is done.' },
    ping: 'Maja joined Storefront relaunch',
    crowd: { value: '6', label: 'people on Storefront relaunch this week' },
  },
  da: {
    title: 'Projekter',
    projects: [
      { name: 'Webshop-relancering', owner: 'Maja K.', people: 6, status: 'I gang', state: 'active', progress: 72 },
      { name: 'Kvartalsrapport Q3', owner: 'Anders L.', people: 3, status: 'Til review', state: 'review', progress: 45 },
      { name: 'Onboarding af kunder', owner: 'Sofie N.', people: 4, status: 'I gang', state: 'active', progress: 88 },
      { name: 'Ny prisside', owner: 'Jonas B.', people: 2, status: 'Afsluttet', state: 'done', progress: 100 },
    ],
    columns: { project: 'Projekt', owner: 'Ejer', people: 'Personer', status: 'Status' },
    nav: ['Projekter', 'Medlemmer', 'Roller', 'Revisionslog', 'Fakturering'],
    kpis: [
      { label: 'Aktive projekter', value: '24' },
      { label: 'Medlemmer', value: '18' },
      { label: 'Hændelser i dag', value: '312' },
    ],
    activeCount: '4 aktive',
    caption: 'Fig. 1 - Projekterne, som dit team ser dem.',
    thisWeek: 'Denne uge',
    peopleSuffix: 'personer',
    note: { title: 'Godt gået, team!', body: 'Ny prisside er færdig.' },
    ping: 'Maja er med på Webshop-relancering',
    crowd: { value: '6', label: 'personer på Webshop-relancering i denne uge' },
  },
}

export function useSample(locale: Locale): Sample {
  return SAMPLE[locale]
}
