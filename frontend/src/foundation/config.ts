/**
 * App-level configuration the foundation reads but the assembly layer owns.
 *
 * `homeRoute` is where authenticated users land (login redirect, sidebar
 * logo, guest-only bounce). It defaults to `/` so the bare foundation works;
 * the product assembly points it at its own home page in `src/main.ts`.
 *
 * `upgradeRoute` is where "upgrade your plan" prompts link, and
 * `onboardingRoute` where a newly registered account goes first; both are set
 * by the module that sells plans (`src/billing`). Without one, upgrade prompts
 * show no link and new accounts land on `homeRoute`.
 */
export interface AppConfig {
  homeRoute: string
  upgradeRoute: string | null
  onboardingRoute: string | null
}

export const appConfig: AppConfig = {
  homeRoute: '/',
  upgradeRoute: null,
  onboardingRoute: null,
}

export function configureApp(overrides: Partial<AppConfig>): void {
  Object.assign(appConfig, overrides)
}
