/**
 * The manifest a product package hands to the app shell - the frontend twin of
 * the backend `ProductModule`. A product declares what it contributes here;
 * the assembly layer (`src/products.ts` -> `main.ts`, `plugins/i18n.ts`)
 * iterates over the installed modules. The platform never imports a product.
 */
export type MessageTree = Record<string, unknown>

export interface ProductModule {
  name: string
  /** Message trees deep-merged over the platform's, per locale. */
  messages: { da: MessageTree; en: MessageTree }
  /** Where signed-in users land; the first product that sets one wins. */
  homeRoute?: string
  /** Startup registrations (nav items, notification presenters). Runs once. */
  setup?: () => void
}
