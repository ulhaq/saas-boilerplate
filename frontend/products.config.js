/**
 * Folder names of the installed product packages under `src/`, for build-time
 * tooling that cannot import the app: `vite.config.ts` (pages, components) and
 * `eslint.config.js` (the platform boundary rule). Keep in sync with the
 * modules listed in `src/products.ts`.
 */
export const productPackages = ['example']
