/**
 * Example product module entry - the manifest of everything the foundation shell
 * needs to know about the product. Listed in `src/products.ts`.
 */
import { FolderOpen, LayoutDashboard } from 'lucide-vue-next'
import da from '@/example/locales/da'
import en from '@/example/locales/en'
import { registerExampleNotifications } from '@/example/notifications'
import { registerNavItems } from '@/foundation/navigation'
import type { Module } from '@/foundation/module'

const example: Module = {
  name: 'example',
  messages: { da, en },
  homeRoute: '/dashboard',
  setup() {
    registerNavItems('main', [
      { to: '/dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, order: 10 },
      { to: '/projects', labelKey: 'nav.projects', icon: FolderOpen, order: 20 },
    ])
    registerExampleNotifications()
  },
}

export default example
