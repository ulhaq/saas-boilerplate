import type { Component } from 'vue'

/**
 * Banners modules show above every dashboard page (e.g. billing's payment and
 * trial notices). Each decides itself whether it renders anything.
 */
const banners: Component[] = []

export function registerBanner(banner: Component): void {
  banners.push(banner)
}

export function registeredBanners(): readonly Component[] {
  return banners
}
