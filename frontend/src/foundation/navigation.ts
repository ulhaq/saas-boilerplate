import type { Component } from 'vue'
import { Bell, ShieldCheck, Users } from '@lucide/vue'

/**
 * Sidebar navigation registry.
 *
 * The foundation owns the groups and its own entries; product modules register
 * additional items at startup (see `src/example/index.ts`). Items render sorted
 * by `order` - foundation entries leave gaps so products can slot in around
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

/**
 * Settings sub-navigation: modules add pages to the settings groups (e.g.
 * billing's subscription page under "organization"). Shown after the
 * foundation's own items, sorted by `order`, to users with `permission`.
 */
export interface SettingsNavItem {
  to: string
  /** i18n key resolved by the settings page at render time. */
  labelKey: string
  icon: Component
  order: number
  permission?: string
}

export type SettingsNavGroup = 'organization' | 'advanced'

const settingsRegistry: Record<SettingsNavGroup, SettingsNavItem[]> = {
  organization: [],
  advanced: [],
}

export function registerSettingsNavItems(group: SettingsNavGroup, items: SettingsNavItem[]): void {
  settingsRegistry[group].push(...items)
  settingsRegistry[group].sort((a, b) => a.order - b.order)
}

export function settingsNavItemsFor(group: SettingsNavGroup): SettingsNavItem[] {
  return settingsRegistry[group]
}
