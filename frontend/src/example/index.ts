/**
 * Example product module entry - registers everything the platform shell needs
 * to know about the product. Imported once from `src/main.ts`.
 */
import { FolderOpen, LayoutDashboard } from 'lucide-vue-next'
import { registerNavItems } from '@/platform/navigation'

registerNavItems('main', [
  { to: '/dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, order: 10 },
  { to: '/projects', labelKey: 'nav.projects', icon: FolderOpen, order: 20 },
])
