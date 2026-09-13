import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Bell,
  CreditCard,
  FolderOpen,
  Globe,
  KeyRound,
  ScrollText,
  ShieldCheck,
  Users,
} from 'lucide-vue-next'

/**
 * The feature catalog shared by the landing page and the dedicated features
 * page. Copy lives under the `landing.features` namespace.
 */
export function useFeatureCatalog() {
  const { t } = useI18n()

  const features = computed(() =>
    [
      { key: 'projects', icon: FolderOpen },
      { key: 'teams', icon: Users },
      { key: 'rbac', icon: ShieldCheck },
      { key: 'billing', icon: CreditCard },
      { key: 'notifications', icon: Bell },
      { key: 'api', icon: KeyRound },
      { key: 'audit', icon: ScrollText },
      { key: 'i18n', icon: Globe },
    ].map((feature) => ({
      ...feature,
      title: t(`landing.features.${feature.key}.title`),
      desc: t(`landing.features.${feature.key}.desc`),
    })),
  )

  return { features }
}
