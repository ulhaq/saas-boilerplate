<route lang="yaml">
meta:
  breadcrumb: nav.apiTokens
  permission: manage:api_token
  planFeature: api_token
</route>

<template>
  <LockedOverlay :feature="PlanFeature.API_TOKEN">
    <div class="animate-fade-in">
      <PageHeader
        :title="$t('settings.apiTokens')"
        :description="$t('settings.apiTokensDescription')"
      >
        <template #actions>
          <Button size="sm" @click="openCreate">
            <Plus class="w-4 h-4 mr-2" />
            {{ $t('settings.createToken') }}
          </Button>
        </template>
      </PageHeader>

      <DataTable
        :columns="columns"
        :items="store.tokens"
        :total="store.tokens.length"
        :loading="loading"
        :row-class="(token) => (token.is_expired ? 'opacity-60' : undefined)"
        :empty-title="$t('settings.noTokens')"
        :empty-description="$t('settings.noTokensDescription')"
        :show-pagination="false"
      >
        <template #row="{ item: token }">
          <TableCell class="font-medium text-sm">{{ token.name }}</TableCell>
          <TableCell class="font-mono text-xs text-muted-foreground">
            sk_{{ token.token_prefix }}...
          </TableCell>
          <TableCell>
            <div class="flex flex-wrap gap-1">
              <Badge
                v-for="perm in token.permissions.slice(0, BADGE_MAX)"
                :key="perm"
                variant="outline"
                class="text-xs"
              >
                {{ perm }}
              </Badge>
              <TooltipProvider v-if="token.permissions.length > BADGE_MAX">
                <Tooltip>
                  <TooltipTrigger>
                    <Badge variant="secondary" class="text-xs cursor-default">
                      +{{ token.permissions.length - BADGE_MAX }}
                    </Badge>
                  </TooltipTrigger>
                  <TooltipContent class="max-w-xs">
                    <div class="flex flex-col gap-1 font-mono text-xs">
                      <span v-for="perm in token.permissions.slice(BADGE_MAX)" :key="perm">{{
                        perm
                      }}</span>
                    </div>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </TableCell>
          <TableCell class="text-xs text-muted-foreground">
            {{ formatDateTime(token.created_at) }}
          </TableCell>
          <TableCell class="text-xs text-muted-foreground">
            <span v-if="token.is_expired" class="inline-flex items-center gap-1.5">
              {{ formatDateTime(token.expires_at!) }}
              <Badge variant="destructive" class="text-[10px] px-1 py-0">{{
                $t('settings.tokenExpired')
              }}</Badge>
            </span>
            <span v-else>{{
              token.expires_at ? formatDateTime(token.expires_at) : $t('settings.tokenNeverExpires')
            }}</span>
          </TableCell>
          <TableCell class="text-xs text-muted-foreground">
            {{
              token.last_used_at
                ? formatDateTime(token.last_used_at)
                : $t('settings.tokenNeverUsed')
            }}
          </TableCell>
        </template>
        <template #actions="{ item: token }">
          <Button
            variant="ghost"
            size="sm"
            class="text-destructive hover:text-destructive hover:bg-destructive/10 h-7 text-xs"
            :disabled="revoking === token.id"
            @click="confirmRevoke(token)"
          >
            <Loader2 v-if="revoking === token.id" class="w-3 h-3 mr-1 animate-spin" />
            {{ $t('settings.revokeToken') }}
          </Button>
        </template>
      </DataTable>

      <!-- Create token dialog -->
      <Dialog v-model:open="createOpen">
        <DialogContent class="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{{ $t('settings.createToken') }}</DialogTitle>
          </DialogHeader>
          <form class="space-y-4 mt-2" @submit.prevent="submitCreate">
            <div class="space-y-2">
              <Label>{{ $t('settings.tokenName') }}</Label>
              <Input
                v-model="form.name"
                :placeholder="$t('settings.tokenNamePlaceholder')"
                :disabled="creating"
                autofocus
              />
              <p v-if="formErrors.name" class="text-xs text-destructive">{{ formErrors.name }}</p>
            </div>
            <div class="space-y-2">
              <Label>{{ $t('settings.tokenExpiry') }}</Label>
              <Select v-model="form.expiryPreset" :disabled="creating">
                <SelectTrigger>
                  <SelectValue :placeholder="$t('settings.tokenExpiryPlaceholder')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="never">{{ $t('settings.expiryNever') }}</SelectItem>
                  <SelectItem value="7d">{{ $t('settings.expiry7d') }}</SelectItem>
                  <SelectItem value="30d">{{ $t('settings.expiry30d') }}</SelectItem>
                  <SelectItem value="60d">{{ $t('settings.expiry60d') }}</SelectItem>
                  <SelectItem value="90d">{{ $t('settings.expiry90d') }}</SelectItem>
                  <SelectItem value="1y">{{ $t('settings.expiry1y') }}</SelectItem>
                  <SelectItem value="custom">{{ $t('settings.expiryCustom') }}</SelectItem>
                </SelectContent>
              </Select>
              <Input
                v-if="form.expiryPreset === 'custom'"
                v-model="form.customDate"
                type="datetime-local"
                :disabled="creating"
                :min="minCustomDate"
              />
            </div>
            <div class="space-y-2">
              <Label>{{ $t('settings.tokenPermissions') }}</Label>
              <p class="text-xs text-muted-foreground">
                {{ $t('settings.tokenPermissionsDescription') }}
              </p>
              <div class="border rounded-md divide-y max-h-48 overflow-y-auto">
                <div
                  v-for="perm in profile.permissions"
                  :key="perm"
                  class="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-muted/50"
                  :class="{ 'opacity-50 cursor-not-allowed': creating }"
                  @click="togglePermission(perm)"
                >
                  <div
                    class="h-4 w-4 shrink-0 rounded-sm border border-primary grid place-content-center transition-colors"
                    :class="form.permissions.includes(perm) ? 'bg-primary' : 'bg-background'"
                  >
                    <Check
                      v-if="form.permissions.includes(perm)"
                      class="h-3 w-3 text-primary-foreground"
                    />
                  </div>
                  <span class="font-mono text-xs select-none">{{ perm }}</span>
                </div>
              </div>
              <p v-if="formErrors.permissions" class="text-xs text-destructive">
                {{ formErrors.permissions }}
              </p>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                :disabled="creating"
                @click="createOpen = false"
              >
                {{ $t('common.cancel') }}
              </Button>
              <Button
                type="submit"
                :disabled="
                  creating ||
                  !form.name.trim() ||
                  (form.expiryPreset === 'custom' && !form.customDate) ||
                  form.permissions.length === 0
                "
              >
                <Loader2 v-if="creating" class="w-4 h-4 mr-2 animate-spin" />
                {{ $t('settings.createToken') }}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <!-- Show new token dialog (one-time) -->
      <Dialog v-model:open="showTokenOpen">
        <DialogContent class="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{{ $t('settings.copyToken') }}</DialogTitle>
            <DialogDescription>{{ $t('settings.copyTokenWarning') }}</DialogDescription>
          </DialogHeader>
          <div class="space-y-3 mt-2">
            <div class="flex items-center gap-2">
              <code
                ref="tokenCodeEl"
                class="flex-1 bg-muted rounded px-3 py-2 text-sm font-mono break-all select-all"
              >
                {{ newToken }}
              </code>
              <Button variant="outline" size="sm" @click="copyToken">
                <Check v-if="copied" class="w-4 h-4" />
                <Copy v-else class="w-4 h-4" />
              </Button>
            </div>
          </div>
          <DialogFooter class="mt-2">
            <Button @click="showTokenOpen = false">{{ $t('common.close') }}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <!-- Revoke confirm dialog -->
      <AlertDialog v-model:open="revokeOpen">
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{{ $t('settings.revokeTokenTitle') }}</AlertDialogTitle>
            <AlertDialogDescription>{{
              $t('settings.revokeTokenDescription')
            }}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{{ $t('common.cancel') }}</AlertDialogCancel>
            <AlertDialogAction
              class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              @click="doRevoke"
            >
              {{ $t('settings.revokeTokenConfirm') }}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  </LockedOverlay>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Loader2, Copy, Check } from 'lucide-vue-next'
import { Button } from '@/platform/components/ui/button'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/platform/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/platform/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from '@/platform/components/ui/alert-dialog'
import { TableCell } from '@/platform/components/ui/table'
import { Badge } from '@/platform/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/platform/components/ui/tooltip'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import DataTable from '@/platform/components/common/DataTable.vue'
import { useApiTokensStore } from '@/platform/stores/apiTokens'
import { useProfileStore } from '@/platform/stores/profile'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { PlanFeature, BADGE_MAX } from '@/platform/constants'
import type { ApiTokenResponse } from '@/platform/types'

const { t } = useI18n()
const { formatDateTime } = useFormatDate()

const columns = [
  { key: 'name', label: t('common.name') },
  { key: 'token_prefix', label: t('settings.columnPrefix') },
  { key: 'permissions', label: t('settings.columnPermissions') },
  { key: 'created_at', label: t('settings.columnCreated') },
  { key: 'expires_at', label: t('settings.columnExpires') },
  { key: 'last_used_at', label: t('settings.columnLastUsed') },
]
const { toast } = useToast()
const { isPlanFeatureError, resolveError } = useErrorHandler()
const store = useApiTokensStore()
const profile = useProfileStore()

const loading = ref(false)
const creating = ref(false)
const revoking = ref<number | null>(null)
const createOpen = ref(false)
const showTokenOpen = ref(false)
const revokeOpen = ref(false)
const newToken = ref('')
const copied = ref(false)
const tokenCodeEl = ref<HTMLElement | null>(null)
const tokenToRevoke = ref<ApiTokenResponse | null>(null)

const form = reactive({
  name: '',
  expiryPreset: 'never',
  customDate: '',
  permissions: [] as string[],
})
const formErrors = reactive({ name: '', customDate: '', permissions: '' })

const minCustomDate = computed(() => {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
})

function resolveExpiresAt(): string | null {
  if (form.expiryPreset === 'never') return null
  if (form.expiryPreset === 'custom') {
    return form.customDate ? new Date(form.customDate).toISOString() : null
  }
  const days: Record<string, number> = { '7d': 7, '30d': 30, '60d': 60, '90d': 90, '1y': 365 }
  const d = new Date()
  d.setDate(d.getDate() + days[form.expiryPreset])
  return d.toISOString()
}

function togglePermission(perm: string) {
  if (creating.value) return
  form.permissions = form.permissions.includes(perm)
    ? form.permissions.filter((p) => p !== perm)
    : [...form.permissions, perm]
}

function openCreate() {
  form.name = ''
  form.expiryPreset = 'never'
  form.customDate = ''
  form.permissions = []
  formErrors.name = ''
  formErrors.customDate = ''
  formErrors.permissions = ''
  createOpen.value = true
}

async function submitCreate() {
  formErrors.name = form.name.trim() ? '' : t('common.nameRequired')
  formErrors.customDate =
    form.expiryPreset === 'custom' && !form.customDate ? t('settings.customDateRequired') : ''
  formErrors.permissions =
    form.permissions.length === 0 ? t('settings.tokenPermissionsRequired') : ''
  if (formErrors.name || formErrors.customDate || formErrors.permissions) return

  creating.value = true
  try {
    const created = await store.createToken({
      name: form.name.trim(),
      permissions: form.permissions,
      expires_at: resolveExpiresAt(),
    })
    createOpen.value = false
    newToken.value = created.token
    copied.value = false
    showTokenOpen.value = true
    toast({ title: t('settings.tokenCreated') })
  } catch (err) {
    if (!isPlanFeatureError(err))
      toast({ title: resolveError(err, t('settings.failedToCreateToken')), variant: 'destructive' })
  } finally {
    creating.value = false
  }
}

watch(showTokenOpen, async (open) => {
  if (!open) return
  await nextTick()
  setTimeout(() => {
    const el = tokenCodeEl.value
    if (!el) return
    const range = document.createRange()
    range.selectNodeContents(el)
    const sel = window.getSelection()
    sel?.removeAllRanges()
    sel?.addRange(range)
  }, 100)
})

async function copyToken() {
  await navigator.clipboard.writeText(newToken.value)
  copied.value = true
  setTimeout(() => {
    copied.value = false
  }, 2000)
  toast({ title: t('settings.tokenCopied') })
}

function confirmRevoke(token: ApiTokenResponse) {
  tokenToRevoke.value = token
  revokeOpen.value = true
}

async function doRevoke() {
  if (!tokenToRevoke.value) return
  revoking.value = tokenToRevoke.value.id
  try {
    await store.revokeToken(tokenToRevoke.value.id)
    toast({ title: t('settings.tokenRevoked') })
  } catch (err) {
    if (!isPlanFeatureError(err))
      toast({ title: resolveError(err, t('settings.failedToRevokeToken')), variant: 'destructive' })
  } finally {
    revoking.value = null
    tokenToRevoke.value = null
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await store.fetchTokens()
  } catch (err) {
    if (!isPlanFeatureError(err))
      toast({ title: resolveError(err, t('settings.failedToLoadTokens')), variant: 'destructive' })
  } finally {
    loading.value = false
  }
})
</script>
