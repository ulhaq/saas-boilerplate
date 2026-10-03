/**
 * What the signed-in organization may use: plan features and per-metric limits
 * - the frontend twin of the backend's `src/foundation/core/entitlements.py`.
 *
 * The foundation asks (API tokens locked? seat limit?) without knowing who
 * answers. A module that sells plans - `src/billing` - installs a provider in
 * its `setup()`; without one, every feature is on and nothing is limited.
 */
/** The organization's plan, for display: a status line and where to manage it. */
export interface PlanSummary {
  label: string
  /** Where this user manages the plan; `null` when they can't. */
  route: string | null
}

export interface Entitlements {
  hasFeature: (feature: string) => boolean
  /** The organization's cap for `metric`; `null` means unlimited. */
  limitFor: (metric: string) => number | null
  /** Load the organization's entitlements; runs when a session starts. */
  load: () => Promise<void>
  /** Refresh the per-metric limits (quota bars, invite limits). */
  loadLimits: () => Promise<void>
  /** Forget everything; runs when the session ends. */
  clear: () => void
  /** The plan to show (e.g. on a dashboard); `null` when there is none. */
  planSummary: () => PlanSummary | null
}

const UNLIMITED: Entitlements = {
  hasFeature: () => true,
  limitFor: () => null,
  load: async () => {},
  loadLimits: async () => {},
  clear: () => {},
  planSummary: () => null,
}

let provider: (() => Entitlements) | null = null

/**
 * Install the provider; call from a module's `setup()`. It is called inside a
 * component or store setup, so it may use Pinia stores.
 */
export function provideEntitlements(factory: () => Entitlements): void {
  if (provider) throw new Error('Another module already provides entitlements')
  provider = factory
}

export function useEntitlements(): Entitlements {
  return provider ? provider() : UNLIMITED
}
