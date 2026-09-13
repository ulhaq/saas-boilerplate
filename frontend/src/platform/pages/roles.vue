<route lang="yaml">
meta:
  layout: dashboard
  requiresAuth: true
  permission: read:role
  breadcrumb: nav.roles
</route>

<template>
  <div class="animate-fade-in">
    <PageHeader :title="$t('roles.title')" :description="$t('roles.description')">
      <template #actions>
        <PermissionGuard permission="create:role">
          <Button size="sm" @click="openCreate">
            <Plus class="w-4 h-4 mr-2" />
            {{ $t('roles.addRole') }}
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
      :empty-title="$t('roles.noRolesFound')"
      :empty-description="$t('roles.createFirstRole')"
      @sort="setSort"
      @update:page="goToPage"
      @update:page-size="setPageSize"
    >
      <template #row="{ item }">
        <TableCell class="font-medium">
          {{ item.name }}
          <Badge v-if="item.is_protected" variant="secondary" class="text-xs ml-2">
            {{ $t('roles.protected') }}
          </Badge>
        </TableCell>
        <TableCell class="text-muted-foreground text-sm">
          {{ item.description || $t('common.noValue') }}
        </TableCell>
        <TableCell>
          <div class="flex flex-wrap gap-1">
            <Badge
              v-for="p in item.permissions.slice(0, BADGE_MAX)"
              :key="p.id"
              variant="outline"
              class="text-xs"
            >
              {{ p.name }}
            </Badge>
            <Badge v-if="item.permissions.length > BADGE_MAX" variant="secondary" class="text-xs">
              +{{ item.permissions.length - BADGE_MAX }}
            </Badge>
            <Badge v-if="!item.permissions.length" variant="warning" class="text-xs">
              {{ $t('roles.noPermissions') }}
            </Badge>
          </div>
        </TableCell>
        <TableCell class="text-muted-foreground text-xs">{{
          formatDate(item.created_at)
        }}</TableCell>
      </template>
      <template #actions="{ item }">
        <DropdownMenu
          v-if="
            item.is_protected ||
            hasAnyPermission(
              'update:role',
              'manage:role_permission',
              'read:permission',
              'delete:role',
            )
          "
        >
          <DropdownMenuTrigger as-child>
            <Button variant="ghost" size="sm" class="h-7 w-7 p-0">
              <MoreHorizontal class="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <template v-if="item.is_protected">
              <DropdownMenuItem class="cursor-pointer" @click="openPermissions(item, true)">
                <Key class="w-4 h-4 mr-2" />{{ $t('roles.viewPermissions') }}
              </DropdownMenuItem>
            </template>
            <template v-else>
              <PermissionGuard permission="update:role">
                <DropdownMenuItem class="cursor-pointer" @click="openEdit(item)">
                  <Pencil class="w-4 h-4 mr-2" />{{ $t('common.edit') }}
                </DropdownMenuItem>
              </PermissionGuard>
              <DropdownMenuItem
                v-if="hasPermission('manage:role_permission')"
                class="cursor-pointer"
                @click="openPermissions(item, false)"
              >
                <Key class="w-4 h-4 mr-2" />{{ $t('roles.managePermissions') }}
              </DropdownMenuItem>
              <DropdownMenuItem
                v-else-if="hasPermission('read:permission')"
                class="cursor-pointer"
                @click="openPermissions(item, true)"
              >
                <Key class="w-4 h-4 mr-2" />{{ $t('roles.viewPermissions') }}
              </DropdownMenuItem>
              <PermissionGuard permission="delete:role">
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  class="cursor-pointer text-destructive focus:text-destructive"
                  @click="handleDelete(item)"
                >
                  <Trash2 class="w-4 h-4 mr-2" />{{ $t('common.delete') }}
                </DropdownMenuItem>
              </PermissionGuard>
            </template>
          </DropdownMenuContent>
        </DropdownMenu>
      </template>
    </DataTable>

    <RoleForm v-model:open="showForm" :role="selectedRole" @saved="onRoleSaved" />
    <RolePermissionDialog
      v-model:open="showPerms"
      :role="selectedRole"
      :readonly="permsReadonly"
      @saved="refresh"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePermission } from '@/platform/composables/usePermission'
import { Plus, MoreHorizontal, Pencil, Trash2, Key } from 'lucide-vue-next'
import { Button } from '@/platform/components/ui/button'
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
import RoleForm from '@/platform/components/roles/RoleForm.vue'
import RolePermissionDialog from '@/platform/components/roles/RolePermissionDialog.vue'
import { useRolesStore } from '@/platform/stores/roles'
import { useDataTable } from '@/platform/composables/useDataTable'
import { useConfirm } from '@/platform/composables/useConfirm'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { BADGE_MAX } from '@/platform/constants'
import type { RoleOut } from '@/platform/types'

const { t } = useI18n()
const { formatDate } = useFormatDate()
const { toast } = useToast()
const rolesStore = useRolesStore()
const { handleError } = useErrorHandler()
const { confirm } = useConfirm()
const { hasPermission, hasAnyPermission } = usePermission()

const columns = [
  { key: 'name', label: t('roles.columns.name'), sortable: true },
  { key: 'description', label: t('roles.columns.description'), sortable: true },
  { key: 'permissions', label: t('roles.columns.permissions') },
  { key: 'created_at', label: t('roles.columns.created'), sortable: true },
]

const { items, total, isLoading, totalPages, pagination, goToPage, setPageSize, setSort, refresh } =
  useDataTable<RoleOut>({ fetcher: rolesStore.list })

const showForm = ref(false)
const showPerms = ref(false)
const permsReadonly = ref(false)
const selectedRole = ref<RoleOut | null>(null)

function openCreate() {
  selectedRole.value = null
  showForm.value = true
}
function openEdit(role: RoleOut) {
  selectedRole.value = role
  showForm.value = true
}
function openPermissions(role: RoleOut, readonly: boolean) {
  selectedRole.value = role
  permsReadonly.value = readonly
  showPerms.value = true
}

function onRoleSaved(newRole: RoleOut | null) {
  refresh()
  if (newRole && hasPermission('manage:role_permission')) {
    selectedRole.value = newRole
    permsReadonly.value = false
    showPerms.value = true
  }
}

async function handleDelete(role: RoleOut) {
  const ok = await confirm(
    t('roles.deleteTitle'),
    t('roles.deleteDescription', { name: role.name }),
    t('common.delete'),
  )
  if (!ok) return
  try {
    await rolesStore.remove(role.id)
    toast({ title: t('roles.deleted') })
    refresh()
  } catch (err: unknown) {
    handleError(err, t('roles.deleteFailed'))
  }
}
</script>
