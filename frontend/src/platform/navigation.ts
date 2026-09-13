import type { Component } from 'vue'
import { Bell, ShieldCheck, Users } from 'lucide-vue-next'

/**
 * Sidebar navigation registry.
 *
 * The platform owns the groups and its own entries; product modules register
 * additional items at startup (see `src/example/index.ts`). Items render sorted
 * by `order` - platform entries leave gaps so products can slot in around
 * them.
 */
export interface NavItem {
  to: string
  /** i18n key resolved by the sidebar at render time. */
  labelKey: string
  icon: Component
  order: number
}

export type NavGroup = 'main' | 'manage'

const registry: Record<NavGroup, NavItem[]> = {
  main: [{ to: '/notifications', labelKey: 'nav.notifications', icon: Bell, order: 30 }],
  manage: [
    { to: '/users', labelKey: 'nav.users', icon: Users, order: 10 },
    { to: '/roles', labelKey: 'nav.roles', icon: ShieldCheck, order: 20 },
  ],
}

export function registerNavItems(group: NavGroup, items: NavItem[]): void {
  registry[group].push(...items)
  registry[group].sort((a, b) => a.order - b.order)
}

export function navItemsFor(group: NavGroup): NavItem[] {
  return registry[group]
}
