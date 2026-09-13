/**
 * App-level configuration the platform reads but the assembly layer owns.
 *
 * `homeRoute` is where authenticated users land (login redirect, sidebar
 * logo, guest-only bounce). It defaults to `/` so the bare platform works;
 * the product assembly points it at its own home page in `src/main.ts`.
 */
export interface AppConfig {
  homeRoute: string
}

export const appConfig: AppConfig = {
  homeRoute: '/',
}

export function configureApp(overrides: Partial<AppConfig>): void {
  Object.assign(appConfig, overrides)
}
