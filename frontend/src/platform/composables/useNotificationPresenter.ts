import { useI18n } from 'vue-i18n'
import type { NotificationOut } from '@/platform/types/notification'

type TranslateFn = ReturnType<typeof useI18n>['t']

export interface NotificationPresenter {
  getTitle: (payload: unknown, t: TranslateFn) => string
  getDescription?: (payload: unknown, t: TranslateFn) => string | null
  getRoute: (payload: unknown) => string | null
  /** ChangeCategory keys to render as coloured badges, if applicable. */
  getCategories?: (payload: unknown) => string[]
  /** Human-readable label for a category badge; platform falls back to the raw key. */
  getCategoryLabel?: (category: string, t: TranslateFn) => string
  /** Tailwind classes for a category badge / dot; platform falls back to a muted style. */
  getCategoryBadgeClass?: (category: string) => string
  getCategoryDotClass?: (category: string) => string
  /** Seed string for the row avatar initials (e.g. a resource name). */
  getAvatarSeed?: (payload: unknown) => string | null
}

const registry = new Map<string, NotificationPresenter>()

export function registerNotificationPresenter(type: string, presenter: NotificationPresenter) {
  registry.set(type, presenter)
}

export function useNotificationPresenter() {
  const { t } = useI18n()

  function getTitle(n: NotificationOut): string {
    return registry.get(n.type)?.getTitle(n.payload, t) ?? t('notifications.title')
  }

  function getDescription(n: NotificationOut): string | null {
    return registry.get(n.type)?.getDescription?.(n.payload, t) ?? null
  }

  function getRoute(n: NotificationOut): string | null {
    return registry.get(n.type)?.getRoute(n.payload) ?? null
  }

  function getCategories(n: NotificationOut): string[] {
    return registry.get(n.type)?.getCategories?.(n.payload) ?? []
  }

  function getAvatarSeed(n: NotificationOut): string | null {
    return registry.get(n.type)?.getAvatarSeed?.(n.payload) ?? null
  }

  function getCategoryLabel(n: NotificationOut, category: string): string {
    return registry.get(n.type)?.getCategoryLabel?.(category, t) ?? category
  }

  function getCategoryBadgeClass(n: NotificationOut, category: string): string {
    return (
      registry.get(n.type)?.getCategoryBadgeClass?.(category) ?? 'bg-muted text-muted-foreground'
    )
  }

  function getCategoryDotClass(n: NotificationOut, category: string): string {
    return registry.get(n.type)?.getCategoryDotClass?.(category) ?? 'bg-muted-foreground'
  }

  return {
    getTitle,
    getDescription,
    getRoute,
    getCategories,
    getAvatarSeed,
    getCategoryLabel,
    getCategoryBadgeClass,
    getCategoryDotClass,
  }
}
