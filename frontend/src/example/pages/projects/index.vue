<route lang="yaml">
meta:
  layout: dashboard
  requiresAuth: true
  permission: read:project
  breadcrumb: nav.projects
</route>

<template>
  <div class="animate-fade-in">
    <PageHeader :title="$t('projects.title')" :description="$t('projects.description')">
      <template #title-suffix>
        <PlanQuota :count="total" :limit="projectLimit" variant="bar" />
      </template>
      <template #actions>
        <PermissionGuard permission="create:project">
          <Button size="sm" @click="openCreate">
            <Plus class="w-4 h-4 mr-2" />
            {{ $t('projects.create') }}
          </Button>
        </PermissionGuard>
      </template>
    </PageHeader>

    <DataTable
      :columns="columns"
      :items="items"
      :total="total"
      :page="pagination.page"
      :page-size="pagination.pageSize"
      :total-pages="totalPages"
      :loading="isLoading"
      :empty-title="$t('projects.emptyTitle')"
      :empty-description="$t('projects.emptyDescription')"
      @sort="setSort"
      @update:page="goToPage"
      @update:page-size="setPageSize"
    >
      <template #toolbar>
        <Input
          v-model="searchQuery"
          :placeholder="$t('projects.searchPlaceholder')"
          class="max-w-xs h-9"
          @input="handleSearch"
        />
        <Button v-if="searchQuery" variant="ghost" size="sm" @click="clearSearch">
          <X class="w-4 h-4" />
        </Button>
      </template>
      <template #row="{ item }">
        <TableCell class="font-medium text-sm">{{ item.name }}</TableCell>
        <TableCell class="text-muted-foreground text-sm max-w-md truncate">
          {{ item.description || '-' }}
        </TableCell>
        <TableCell class="text-muted-foreground text-xs">
          {{ formatDate(item.created_at) }}
        </TableCell>
      </template>
      <template #actions="{ item }">
        <DropdownMenu v-if="hasAnyPermission('update:project', 'delete:project')">
          <DropdownMenuTrigger as-child>
            <Button variant="ghost" size="sm" class="h-7 w-7 p-0">
              <MoreHorizontal class="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <PermissionGuard permission="update:project">
              <DropdownMenuItem class="cursor-pointer" @click="openEdit(item)">
                <Pencil class="w-4 h-4 mr-2" />
                {{ $t('common.edit') }}
              </DropdownMenuItem>
            </PermissionGuard>
            <PermissionGuard permission="delete:project">
              <DropdownMenuSeparator />
              <DropdownMenuItem
                class="cursor-pointer text-destructive focus:text-destructive"
                @click="handleDelete(item)"
              >
                <Trash2 class="w-4 h-4 mr-2" />
                {{ $t('common.delete') }}
              </DropdownMenuItem>
            </PermissionGuard>
          </DropdownMenuContent>
        </DropdownMenu>
      </template>
    </DataTable>

    <ProjectForm v-model:open="showForm" :project="selectedProject" @saved="refresh" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { MoreHorizontal, Pencil, Plus, Trash2, X } from 'lucide-vue-next'
import { Button } from '@/platform/components/ui/button'
import { Input } from '@/platform/components/ui/input'
import { TableCell } from '@/platform/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/platform/components/ui/dropdown-menu'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import DataTable from '@/platform/components/common/DataTable.vue'
import PermissionGuard from '@/platform/components/common/PermissionGuard.vue'
import PlanQuota from '@/platform/components/common/PlanQuota.vue'
import ProjectForm from '@/example/components/projects/ProjectForm.vue'
import { useProjectsStore } from '@/example/stores/projects'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useDataTable } from '@/platform/composables/useDataTable'
import { usePermission } from '@/platform/composables/usePermission'
import { useConfirm } from '@/platform/composables/useConfirm'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { ExampleUsageMetric } from '@/example/constants'
import type { ProjectOut } from '@/example/types/project'

const { t } = useI18n()
const projectsStore = useProjectsStore()
const subscriptionStore = useSubscriptionStore()
const { formatDate } = useFormatDate()
const { toast } = useToast()
const { handleError } = useErrorHandler()
const { confirm } = useConfirm()
const { hasAnyPermission } = usePermission()

const columns = [
  { key: 'name', label: t('projects.columns.name'), sortable: true },
  { key: 'description', label: t('projects.columns.description') },
  { key: 'created_at', label: t('projects.columns.created'), sortable: true },
]

const {
  items,
  total,
  isLoading,
  totalPages,
  pagination,
  goToPage,
  setPageSize,
  setSort,
  setSearch,
  refresh,
} = useDataTable<ProjectOut>({ fetcher: projectsStore.list })

const projectLimit = computed(() => subscriptionStore.limitFor(ExampleUsageMetric.PROJECTS))

const searchQuery = ref('')
let searchTimeout: ReturnType<typeof setTimeout>

function handleSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    setSearch(searchQuery.value || undefined)
  }, 300)
}

function clearSearch() {
  searchQuery.value = ''
  setSearch(undefined)
}

onMounted(() => subscriptionStore.fetchUsage())

const showForm = ref(false)
const selectedProject = ref<ProjectOut | null>(null)

function openCreate() {
  selectedProject.value = null
  showForm.value = true
}

function openEdit(project: ProjectOut) {
  selectedProject.value = project
  showForm.value = true
}

async function handleDelete(project: ProjectOut) {
  const ok = await confirm(
    t('projects.deleteTitle'),
    t('projects.deleteDescription', { name: project.name }),
    t('common.delete'),
  )
  if (!ok) return
  try {
    await projectsStore.remove(project.id)
    toast({ title: t('projects.deleted') })
    refresh()
  } catch (err: unknown) {
    handleError(err, t('projects.deleteFailed'))
  }
}
</script>
