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
- `src/i18n/routes.ts` - the page inventory: one key per page with its slug per locale. Links, the language switch and hreflang tags are built from it. The legal slugs are linked from the app (`LEGAL_PATHS` in `frontend/src/platform/constants.ts`); keep them in sync.
- `src/i18n/ui.ts` - all copy, `en` first; `da` is typed against it, so a missing key fails `npm run check`.
- `src/content/plans.ts` - plans, prices and the comparison table. Static: keep in sync with the plan seeds and the app's `planComparisonRows`.
- `src/content/legal/` - privacy policy and terms per locale (templates - get them reviewed before launch).
- `src/views/` - one view per page, taking `locale`. `src/pages/<locale>/<slug>.astro` are thin wrappers, so localized slugs stay plain files.
- `src/styles/global.css` - the base layer: layout and structure for every component, drawn from tokens (`@layer base`). Components have no scoped styles; they use these plain class names.
- `src/themes/<name>/` - one folder per design: `config.ts` (step numbering, which highlight strip to show, browser theme colour), `theme.css` (font imports, tokens and overrides in `@layer theme`) and `HeroVisual.astro` (the front-page picture). The contract is in `src/themes/types.ts`.
- `src/content/sample.ts` - the example projects the hero visuals draw.

## Themes

`SITE_THEME` (in `site/.env`, read at build time) picks the design: `editorial` (default), `tech`, `soft`, `swiss`, `brutal`, `enterprise`, `nordic` or `aurora`. `astro.config.mjs` aliases `@theme` to `src/themes/<SITE_THEME>/`, so only that theme's CSS, fonts and hero visual are bundled; an unknown name fails the build and lists the valid ones. Restart the dev server after changing it.

- `@layer theme` always beats `@layer base`, so a theme overrides with plain selectors and no specificity games. Change shared structure in `global.css`; change looks in the theme.
- Prefix class names inside a `HeroVisual.astro` (`tv-`, `sv-`, ...). Scoped styles still match global classes of the same name.
- Adding a theme: copy the closest folder, rename it, and it becomes a valid `SITE_THEME`. Only `editorial` has a dark mode; `tech` and `aurora` are dark only; the rest are light only.

## Conventions

- Adding a page: add it to `PAGES`, add `meta.<key>` and its copy to both locales, write the view, and add one wrapper per locale.
- Forms (`form[data-api]`, `src/scripts/forms.ts`) post JSON to same-origin `/v1/...`. The dev server and the image's nginx (`nginx.conf.template`) proxy only `/v1/contact` and `/v1/waitlist` to the backend, so no CORS config is needed. A new endpoint must be added to the nginx allowlist.
- `PUBLIC_CTA_MODE=waitlist` swaps every call to action for the waitlist form on the front page and hides the login link. `CtaLink.astro` and `Plans.astro` handle the switch.
- The site sets no cookies, so it has no consent banner. Keep it that way, or bring back consent handling.
