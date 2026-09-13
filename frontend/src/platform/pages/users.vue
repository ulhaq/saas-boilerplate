<route lang="yaml">
meta:
  layout: dashboard
  requiresAuth: true
  permission: read:user
  breadcrumb: nav.users
</route>

<template>
  <div class="animate-fade-in">
    <PageHeader :title="$t('users.title')" :description="$t('users.description')">
      <template #title-suffix>
        <PlanQuota :count="total" :limit="subscriptionStore.seatLimit" variant="bar" />
      </template>
      <template #actions>
        <PermissionGuard permission="manage:organization_user">
          <Button size="sm" @click="openInvite">
            <Mail class="w-4 h-4 mr-2" />
            {{ $t('users.invite.button') }}
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
      :empty-title="$t('users.noUsersFound')"
      :empty-description="$t('users.createFirstUser')"
      @sort="setSort"
      @update:page="goToPage"
      @update:page-size="setPageSize"
    >
      <template #toolbar>
        <Input
          v-model="searchQuery"
          :placeholder="$t('users.searchPlaceholder')"
          class="max-w-xs h-9"
          @input="handleSearch"
        />
        <Button v-if="searchQuery" variant="ghost" size="sm" @click="clearSearch">
          <X class="w-4 h-4" />
        </Button>
      </template>
      <template #row="{ item }">
        <TableCell>
          <div class="flex items-center gap-3">
            <div
              class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0"
            >
              <span class="text-xs font-medium text-primary">{{ initials(item.name) }}</span>
            </div>
            <div>
              <p class="font-medium text-sm">{{ item.name }}</p>
              <p class="text-xs text-muted-foreground">{{ item.email }}</p>
            </div>
          </div>
        </TableCell>
        <TableCell>
          <div class="flex flex-wrap gap-1">
            <Badge
              v-for="role in item.roles.slice(0, BADGE_MAX)"
              :key="role.id"
              variant="secondary"
              class="text-xs"
            >
              {{ role.name }}
            </Badge>
            <Badge v-if="item.roles.length > BADGE_MAX" variant="outline" class="text-xs">
              +{{ item.roles.length - BADGE_MAX }}
            </Badge>
            <Badge v-if="!item.roles.length" variant="warning" class="text-xs">
              {{ $t('users.noRoles') }}
            </Badge>
          </div>
        </TableCell>
        <TableCell class="text-muted-foreground text-xs">
          {{ formatDate(item.created_at) }}
        </TableCell>
      </template>
      <template #actions="{ item }">
        <DropdownMenu v-if="hasAnyPermission('manage:organization_user', 'manage:user_role')">
          <DropdownMenuTrigger as-child>
            <Button variant="ghost" size="sm" class="h-7 w-7 p-0">
              <MoreHorizontal class="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <PermissionGuard permission="manage:organization_user">
              <DropdownMenuItem class="cursor-pointer" @click="openEdit(item)">
                <Pencil class="w-4 h-4 mr-2" />
                {{ $t('common.edit') }}
              </DropdownMenuItem>
            </PermissionGuard>
            <PermissionGuard permission="manage:user_role">
              <DropdownMenuItem class="cursor-pointer" @click="openRoles(item)">
                <Shield class="w-4 h-4 mr-2" />
                {{ $t('users.manageRoles') }}
              </DropdownMenuItem>
            </PermissionGuard>
            <PermissionGuard permission="manage:organization_user">
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

    <UserForm v-model:open="showForm" :user="selectedUser" @saved="refresh" />
    <UserRoleDialog v-model:open="showRoles" :user="selectedUser" @saved="refresh" />
    <InviteUserDialog v-model:open="showInvite" @invited="refresh" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Mail, MoreHorizontal, Pencil, Trash2, Shield, X } from 'lucide-vue-next'
import { Button } from '@/platform/components/ui/button'
import { Input } from '@/platform/components/ui/input'
import { Badge } from '@/platform/components/ui/badge'
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
import UserForm from '@/platform/components/users/UserForm.vue'
import UserRoleDialog from '@/platform/components/users/UserRoleDialog.vue'
import InviteUserDialog from '@/platform/components/users/InviteUserDialog.vue'
import { useUsersStore } from '@/platform/stores/users'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useDataTable } from '@/platform/composables/useDataTable'
import { usePermission } from '@/platform/composables/usePermission'
import { useConfirm } from '@/platform/composables/useConfirm'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { BADGE_MAX } from '@/platform/constants'
import type { UserOut } from '@/platform/types'

const { t } = useI18n()
const subscriptionStore = useSubscriptionStore()
const usersStore = useUsersStore()
const { formatDate } = useFormatDate()
const { toast } = useToast()
const { handleError } = useErrorHandler()
const { confirm } = useConfirm()
const { hasAnyPermission } = usePermission()

const columns = [
  { key: 'name', label: t('users.columns.user'), sortable: true },
  { key: 'roles', label: t('users.columns.roles') },
  { key: 'created_at', label: t('users.columns.created'), sortable: true },
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
} = useDataTable<UserOut>({ fetcher: usersStore.list })

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
const showRoles = ref(false)
const showInvite = ref(false)
const selectedUser = ref<UserOut | null>(null)

function openInvite() {
  showInvite.value = true
}

function openEdit(user: UserOut) {
  selectedUser.value = user
  showForm.value = true
}

function openRoles(user: UserOut) {
  selectedUser.value = user
  showRoles.value = true
}

async function handleDelete(user: UserOut) {
  const ok = await confirm(
    t('users.deleteTitle'),
    t('users.deleteDescription', { name: user.name }),
    t('common.delete'),
  )
  if (!ok) return
  try {
    await usersStore.removeFromOrganization(user.id)
    toast({ title: t('users.deleted') })
    refresh()
  } catch (err: unknown) {
    handleError(err, t('users.deleteFailed'))
  }
}

function initials(name: string) {
  return name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}
</script>
