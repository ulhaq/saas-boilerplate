# CLAUDE.md

The public marketing site: landing, features, pricing, about, contact and the legal pages, in Danish and English. A standalone static [Astro](https://astro.build) site. It shares no code with `frontend/` or `backend/`, and ships no JS except the small form script.

## Commands

```bash
npm run dev      # http://localhost:4321, proxies /v1 to API_TARGET
npm run check    # astro check (types)
npm run build    # static output in dist/
```

## Layout

- `src/config.ts` - product name, company details, support email, and env-driven settings (`PUBLIC_APP_URL`, `PUBLIC_CTA_MODE`, ...). See `.env.example`.
- `src/i18n/routes.ts` - the page inventory: one key per page with its slug per locale. Links, the language switch and hreflang tags are built from it. The legal slugs are linked from the app (`LEGAL_PATHS` in `frontend/src/foundation/constants.ts`); keep them in sync.
- `src/i18n/ui.ts` - all copy, `en` first; `da` is typed against it, so a missing key fails `npm run check`.
- `src/content/plans.ts` - plans, prices (monthly `amount` and `yearly`, per currency) and the comparison table. Static: keep in sync with the plan seeds and the app's `planComparisonRows`. The pricing cards render every currency × period and switch between them with JS (`components/Plans.astro`); the choice is remembered and added to links into the app as `?currency=` / `?interval=` (`scripts/currency.ts`), which the app's billing page adopts.
- `src/content/legal/` - privacy policy and terms per locale (templates - get them reviewed before launch).
- `src/views/` - one view per page, taking `locale`. `src/pages/<locale>/<slug>.astro` are thin wrappers, so localized slugs stay plain files.
- `src/styles/global.css` - the base layer: layout and structure for every component, drawn from tokens (`@layer base`). Components have no scoped styles; they use these plain class names.
- `src/themes/<name>/` - one folder per design: `config.ts` (step numbering, which highlight strip to show, browser theme colour), `theme.css` (font imports, tokens and overrides in `@layer theme`) and `HeroVisual.astro` (the front-page picture). The contract is in `src/themes/types.ts`.
- `src/content/structuredData.ts` - the pages' schema.org JSON-LD (`jsonLd` prop of `Base.astro`): the organization, website and product with one offer per plan, currency and period (from `plans.ts`, excl. VAT) on the front page; the product on pricing; `FAQPage` for the FAQ the front page and pricing show. Built only from what the page shows - never add ratings or reviews that aren't real. `public/logo.png` (its `logo`) is a copy of the app's `frontend/public/logo.png`.
- `/` redirects by the browser's language: Caddy (`Caddyfile`, 302 on `Accept-Language`) and `src/pages/index.astro` as a fallback, both keeping the query string. It is the front page's hreflang x-default; every other page's x-default is its `DEFAULT_LOCALE` version (`xDefaultPath`).
- `src/content/sample.ts` - the example projects the hero visuals draw.

## Themes

`SITE_THEME` (in `site/.env`, read at build time) picks the design: `editorial` (default), `tech`, `soft`, `swiss`, `brutal`, `enterprise`, `nordic` or `aurora`. `astro.config.mjs` aliases `@theme` to `src/themes/<SITE_THEME>/`, so only that theme's CSS, fonts and hero visual are bundled; an unknown name fails the build and lists the valid ones. Restart the dev server after changing it.

- `@layer theme` always beats `@layer base`, so a theme overrides with plain selectors and no specificity games. Change shared structure in `global.css`; change looks in the theme.
- Prefix class names inside a `HeroVisual.astro` (`tv-`, `sv-`, ...). Scoped styles still match global classes of the same name.
- Adding a theme: copy the closest folder, rename it, and it becomes a valid `SITE_THEME`. Only `editorial` has a dark mode; `tech` and `aurora` are dark only; the rest are light only.

## Conventions

- Adding a page: add it to `PAGES`, add `meta.<key>` and its copy to both locales, write the view, and add one wrapper per locale.
- Forms (`form[data-api]`, `src/scripts/forms.ts`) post JSON to same-origin `/v1/...`. The dev server and the image's Caddy (`Caddyfile`) proxy only `/v1/contact` and `/v1/waitlist` to the backend (the marketing module, `backend/src/marketing/`), so no CORS config is needed. A new endpoint must be added to the Caddy allowlist.
- `PUBLIC_CTA_MODE=waitlist` swaps every call to action for the waitlist form on the front page and hides the login link. `CtaLink.astro` and `Plans.astro` handle the switch.
- The site sets no cookies, so it has no consent banner. Keep it that way, or bring back consent handling.
