import type { RouteLocationNormalized, RouteLocationRaw } from 'vue-router'

/**
 * Extra navigation guards modules add for signed-in users (e.g. billing sends
 * an organization without access to its billing page). Run in registration
 * order by the router after the platform's own checks; the first redirect wins.
 */
export type RouteGuard = (to: RouteLocationNormalized) => RouteLocationRaw | undefined

const guards: RouteGuard[] = []

export function registerRouteGuard(guard: RouteGuard): void {
  guards.push(guard)
}

export function routeGuards(): readonly RouteGuard[] {
  return guards
}
