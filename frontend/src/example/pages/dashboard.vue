<route lang="yaml">
meta:
  layout: dashboard
  requiresAuth: true
  breadcrumb: nav.dashboard
</route>

<template>
  <div class="animate-fade-in space-y-6">
    <PageHeader :title="$t('dashboard.title')" :description="$t('dashboard.description')" />

    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <StatCard
        :label="$t('dashboard.projects')"
        :value="canReadProjects ? projectTotal : '-'"
        :hint="projectHint"
        :icon="FolderOpen"
        :loading="loading"
        icon-bg="bg-blue-50 dark:bg-blue-950"
        icon-color="text-blue-500"
        :to="canReadProjects ? '/projects' : undefined"
      />
      <StatCard
        :label="$t('dashboard.plan')"
        :value="planStatusLabel"
        :icon="CreditCard"
        :loading="loading"
        icon-bg="bg-emerald-50 dark:bg-emerald-950"
        icon-color="text-emerald-500"
        :to="hasPermission('manage:subscription') ? '/settings/billing' : undefined"
      />
      <StatCard
        :label="$t('dashboard.notifications')"
        :value="notificationsStore.unreadCount"
        :hint="$t('dashboard.unread')"
        :icon="Bell"
        :loading="loading"
        icon-bg="bg-amber-50 dark:bg-amber-950"
        icon-color="text-amber-500"
        to="/notifications"
      />
    </div>

    <div v-if="canReadProjects" class="rounded-lg border bg-card">
      <div class="flex items-center justify-between px-5 py-4 border-b">
        <h2 class="font-semibold">{{ $t('dashboard.recentProjects') }}</h2>
        <RouterLink
          to="/projects"
          class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          {{ $t('dashboard.viewAll') }}
          <ArrowRight class="w-4 h-4" />
        </RouterLink>
      </div>

      <div v-if="loading" class="p-5 space-y-3">
        <Skeleton v-for="n in 3" :key="n" class="h-10 w-full" />
      </div>
      <EmptyState
        v-else-if="recentProjects.length === 0"
        :title="$t('dashboard.emptyTitle')"
        :description="$t('dashboard.emptyDescription')"
        :icon="FolderOpen"
      >
        <PermissionGuard permission="create:project">
          <Button as-child size="sm" class="mt-4">
            <RouterLink to="/projects">
              <Plus class="w-4 h-4 mr-2" />
              {{ $t('dashboard.emptyCta') }}
            </RouterLink>
          </Button>
        </PermissionGuard>
      </EmptyState>
      <ul v-else class="divide-y">
        <li
          v-for="project in recentProjects"
          :key="project.id"
          class="flex items-center justify-between gap-4 px-5 py-3"
        >
          <div class="min-w-0">
            <p class="text-sm font-medium truncate">{{ project.name }}</p>
            <p v-if="project.description" class="text-xs text-muted-foreground truncate">
              {{ project.description }}
            </p>
          </div>
          <span class="shrink-0 text-xs text-muted-foreground">
            {{ formatRelativeTime(project.created_at) }}
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ArrowRight, Bell, CreditCard, FolderOpen, Plus } from 'lucide-vue-next'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import StatCard from '@/platform/components/common/StatCard.vue'
import EmptyState from '@/platform/components/common/EmptyState.vue'
import PermissionGuard from '@/platform/components/common/PermissionGuard.vue'
import { Button } from '@/platform/components/ui/button'
import { Skeleton } from '@/platform/components/ui/skeleton'
import { useProjectsStore } from '@/example/stores/projects'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useNotificationsStore } from '@/platform/stores/notifications'
import { usePermission } from '@/platform/composables/usePermission'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { ExampleUsageMetric } from '@/example/constants'
import type { ProjectOut } from '@/example/types/project'

const { t, te } = useI18n()
const { hasPermission } = usePermission()
const { formatRelativeTime } = useFormatDate()
const projectsStore = useProjectsStore()
const subscription = useSubscriptionStore()
const notificationsStore = useNotificationsStore()

const loading = ref(true)
const projectTotal = ref(0)
const recentProjects = ref<ProjectOut[]>([])

const canReadProjects = computed(() => hasPermission('read:project'))

const projectHint = computed(() => {
  const limit = subscription.limitFor(ExampleUsageMetric.PROJECTS)
  return limit === null ? undefined : t('dashboard.ofLimit', { limit })
})

const planStatusLabel = computed(() => {
  const status = subscription.subscriptionStatus
  if (!status) return '-'
  const key = `subscription.status.${status}`
  return te(key) ? t(key) : status
})

onMounted(async () => {
  try {
    const tasks: Promise<unknown>[] = [subscription.fetchUsage()]
    if (canReadProjects.value) {
      tasks.push(
        projectsStore.list({ page_size: 5, sort: '-created_at' }).then((page) => {
          projectTotal.value = page.total
          recentProjects.value = page.items
        }),
      )
    }
    await Promise.all(tasks)
  } finally {
    loading.value = false
  }
})
</script>
