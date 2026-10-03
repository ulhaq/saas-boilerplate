/**
 * The manifest a module - the product or an optional foundation module (billing)
 * - hands to the app shell; the frontend twin of the backend `Module`. The
 * assembly layer (`src/products.ts` -> `main.ts`, `plugins/i18n.ts`) iterates
 * over the installed modules. The foundation never imports a module.
 */
export type MessageTree = Record<string, unknown>

export interface Module {
  name: string
  /** Message trees deep-merged over the foundation's, per locale. */
  messages: { da: MessageTree; en: MessageTree }
  /** Where signed-in users land; the first product that sets one wins. */
  homeRoute?: string
  /** Startup registrations (nav items, notification presenters). Runs once. */
  setup?: () => void
}
