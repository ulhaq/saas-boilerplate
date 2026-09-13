<template>
  <div class="flex flex-col h-full">
    <!-- Logo -->
    <RouterLink
      :to="appConfig.homeRoute"
      class="flex items-center gap-2 px-4 h-16 shrink-0 border-b border-sidebar-border hover:opacity-80 transition-opacity"
    >
      <div class="flex items-center justify-center w-8 h-8 rounded-lg bg-sidebar-primary shrink-0">
        <Radar class="w-4 h-4 text-sidebar-primary-foreground" />
      </div>
      <span class="font-semibold text-sidebar-foreground">{{ $t('app.name') }}</span>
    </RouterLink>

    <!-- Organization Switcher -->
    <div
      v-if="showOrganizationMenu"
      class="flex items-center px-3 h-16 shrink-0 border-b border-sidebar-border"
    >
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <button
            class="w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
          >
            <Building2 class="w-4 h-4 shrink-0 text-sidebar-foreground/60" />
            <span class="flex-1 text-left truncate font-medium">{{ currentOrganizationName }}</span>
            <ChevronsUpDown class="w-3.5 h-3.5 text-sidebar-foreground/50" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent class="w-52" align="start">
          <DropdownMenuLabel class="text-xs text-muted-foreground">{{
            $t('nav.switchOrganization')
          }}</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            v-for="organization in organizations"
            :key="organization.id"
            class="cursor-pointer"
            @click="handleSwitchOrganization(organization.id)"
          >
            <Check v-if="currentOrganizationId === organization.id" class="w-4 h-4 mr-2" />
            <span v-else class="w-4 h-4 mr-2" />
            {{ organization.name }}
          </DropdownMenuItem>
          <template v-if="allowMultipleOrganizations">
            <DropdownMenuSeparator />
            <DropdownMenuItem class="cursor-pointer" @click="showCreate = true">
              <Plus class="w-4 h-4 mr-2" />
              {{ $t('organizations.createOrganization') }}
            </DropdownMenuItem>
          </template>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>

    <OrganizationForm v-model:open="showCreate" />

    <!-- Navigation -->
    <nav class="flex-1 px-3 py-4 space-y-4 overflow-y-auto">
      <div v-for="group in navGroups" :key="group.label">
        <p
          class="px-3 mb-1 text-xs font-semibold text-sidebar-foreground/40 uppercase tracking-wider"
        >
          {{ group.label }}
        </p>
        <div class="space-y-0.5">
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="relative flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all"
            :class="
              isActive(item.to)
                ? 'bg-sidebar-accent text-sidebar-accent-foreground shadow-sm before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-0.5 before:rounded-full before:bg-sidebar-primary'
                : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground'
            "
          >
            <component :is="item.icon" class="w-4 h-4 shrink-0" />
            <span class="flex-1">{{ item.label }}</span>
          </RouterLink>
        </div>
      </div>
    </nav>

    <!-- User / Settings -->
    <div class="px-3 py-2 border-t border-sidebar-border">
      <RouterLink
        to="/settings"
        class="flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-all"
        :class="
          isActive('/settings')
            ? 'bg-sidebar-accent text-sidebar-accent-foreground shadow-sm'
            : 'text-sidebar-foreground/70 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground'
        "
      >
        <div
          class="w-7 h-7 rounded-full bg-sidebar-primary flex items-center justify-center shrink-0"
        >
          <span class="text-sidebar-primary-foreground text-xs font-semibold">
            {{ userInitials }}
          </span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-medium text-sidebar-foreground truncate">{{ user?.name }}</p>
          <p class="text-xs text-sidebar-foreground/50 truncate">{{ user?.email }}</p>
        </div>
        <Settings class="w-4 h-4 shrink-0 opacity-40" />
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Settings, Check, ChevronsUpDown, Building2, Radar, Plus } from 'lucide-vue-next'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/platform/components/ui/dropdown-menu'
import OrganizationForm from '@/platform/components/organizations/OrganizationForm.vue'
import { useAuthStore } from '@/platform/stores/auth'
import { useProfileStore } from '@/platform/stores/profile'
import { useOrganizationsStore } from '@/platform/stores/organizations'
import { useSessionStore } from '@/platform/stores/session'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { navItemsFor } from '@/platform/navigation'
import { appConfig } from '@/platform/config'
import { ALLOW_MULTIPLE_ORGANIZATIONS } from '@/platform/constants'

const authStore = useAuthStore()
const profileStore = useProfileStore()
const organizationStore = useOrganizationsStore()
const sessionStore = useSessionStore()
const route = useRoute()
const { handleError } = useErrorHandler()
const { t } = useI18n()

const user = computed(() => profileStore.user)
const organizations = computed(() => organizationStore.organizations)

const allowMultipleOrganizations = ALLOW_MULTIPLE_ORGANIZATIONS
const showCreate = ref(false)

// Show the org menu when there are multiple orgs to switch between, or when the
// user is allowed to create one (so "New organization" stays reachable).
const showOrganizationMenu = computed(
  () => organizations.value.length > 1 || allowMultipleOrganizations,
)

const userInitials = computed(() => {
  if (!user.value?.name) return '?'
  return user.value.name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
})

const currentOrganizationId = computed(() => {
  const token = sessionStore.accessToken
  if (!token) return null
  try {
    const payload = JSON.parse(atob(token.split('.')[1]!))
    return payload.oid as number | null
  } catch {
    return null
  }
})

const currentOrganizationName = computed(() => {
  const organization = organizations.value.find((o) => o.id === currentOrganizationId.value)
  return organization?.name ?? t('nav.organization')
})

const navGroups = computed(() => [
  {
    label: t('nav.main'),
    items: navItemsFor('main').map((i) => ({ ...i, label: t(i.labelKey) })),
  },
  {
    label: t('nav.manage'),
    items: navItemsFor('manage').map((i) => ({ ...i, label: t(i.labelKey) })),
  },
])

function isActive(path: string): boolean {
  if (path === appConfig.homeRoute) return route.path === appConfig.homeRoute
  return route.path.startsWith(path)
}

async function handleSwitchOrganization(organizationId: number) {
  if (organizationId === currentOrganizationId.value) return
  try {
    await authStore.switchOrganization(organizationId)
    window.location.reload()
  } catch (err: unknown) {
    handleError(err, t('nav.failedToSwitchOrganization'))
  }
}
</script>
