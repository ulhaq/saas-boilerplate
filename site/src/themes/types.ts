/**
 * The contract every theme in `src/themes/<name>/` fulfils:
 *
 * - `config.ts`        default-exports a `ThemeConfig`
 * - `theme.css`        font imports, then tokens and overrides in `@layer theme`
 * - `HeroVisual.astro` the picture beside (or under) the front-page headline;
 *                      takes `{ locale }` and draws from `content/sample.ts`
 *
 * `SITE_THEME` picks the folder at build time: astro.config.mjs aliases
 * `@theme` to it, so only that theme's CSS, fonts and visual are bundled.
 */
export interface ThemeConfig {
  /** How step numbers are set in "How it works". */
  stepMarks: 'roman' | 'digits' | 'code' | 'words'
  /**
   * The highlight items (`highlights` in the copy), if any: a band of stats
   * under the hero, a scrolling ticker above the header, or check badges.
   */
  highlights: 'band' | 'ticker' | 'badges' | null
  /** Browser UI colour (`<meta name="theme-color">`) per scheme. */
  themeColor: { light: string; dark?: string }
}

const WORDS = {
  en: ['one', 'two', 'three', 'four'],
  da: ['en', 'to', 'tre', 'fire'],
}
const ROMAN = ['i.', 'ii.', 'iii.', 'iv.']

/** The mark for step `i` (0-based) in the theme's style. */
export function stepMark(style: ThemeConfig['stepMarks'], i: number, locale: 'da' | 'en'): string {
  switch (style) {
    case 'roman':
      return ROMAN[i]
    case 'code':
      return `STEP_${String(i + 1).padStart(2, '0')}`
    case 'words':
      return WORDS[locale][i]
    default:
      return String(i + 1)
  }
}
