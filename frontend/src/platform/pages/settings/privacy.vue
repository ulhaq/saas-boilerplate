<route lang="yaml">
meta:
  breadcrumb: gdpr.title
</route>

<template>
  <div class="max-w-2xl animate-fade-in">
    <PageHeader :title="$t('gdpr.title')" :description="$t('gdpr.description')" />

    <!-- Export Data -->
    <Card class="mt-6">
      <CardContent class="pt-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p class="font-medium text-sm">{{ $t('gdpr.exportTitle') }}</p>
          <p class="text-sm text-muted-foreground mt-0.5">{{ $t('gdpr.exportDescription') }}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          class="shrink-0 w-full sm:w-auto"
          :disabled="exporting"
          @click="handleExport"
        >
          <Loader2 v-if="exporting" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('gdpr.exportButton') }}
        </Button>
      </CardContent>
    </Card>

    <!-- Delete Account -->
    <div class="mt-8">
      <h2 class="text-sm font-semibold text-destructive uppercase tracking-wider mb-3">
        {{ $t('settings.dangerZone') }}
      </h2>
      <Card class="border-destructive/50">
        <CardContent class="pt-6">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p class="font-medium text-sm">{{ $t('gdpr.deleteTitle') }}</p>
              <p class="text-sm text-muted-foreground mt-0.5">{{ $t('gdpr.deleteDescription') }}</p>
            </div>
            <Button
              variant="destructive"
              size="sm"
              class="shrink-0 w-full sm:w-auto"
              :disabled="deleting"
              @click="showDeleteForm = true"
            >
              {{ $t('gdpr.deleteButton') }}
            </Button>
          </div>

          <form
            v-if="showDeleteForm"
            class="mt-4 space-y-3 border-t pt-4"
            @submit.prevent="handleDelete"
          >
            <div class="space-y-2">
              <Label for="delete-password">{{ $t('gdpr.deletePasswordLabel') }}</Label>
              <PasswordInput
                id="delete-password"
                v-model="deletePassword"
                :placeholder="$t('gdpr.deletePasswordPlaceholder')"
                :disabled="deleting"
                autofocus
              />
            </div>
            <p v-if="deleteError" class="text-sm text-destructive">{{ deleteError }}</p>
            <div class="flex gap-2 justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                :disabled="deleting"
                @click="cancelDelete"
              >
                {{ $t('common.cancel') }}
              </Button>
              <Button
                type="submit"
                variant="destructive"
                size="sm"
                :disabled="deleting || !deletePassword"
              >
                <Loader2 v-if="deleting" class="w-4 h-4 mr-2 animate-spin" />
                {{ $t('gdpr.deleteConfirm') }}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Loader2 } from 'lucide-vue-next'
import { Card, CardContent } from '@/platform/components/ui/card'
import { Button } from '@/platform/components/ui/button'
import { Label } from '@/platform/components/ui/label'
import { useToast } from '@/platform/components/ui/toast'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import { useGdprStore } from '@/platform/stores/gdpr'
import { useAuthStore } from '@/platform/stores/auth'
import { useConfirm } from '@/platform/composables/useConfirm'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'

const router = useRouter()
const { t } = useI18n()
const gdprStore = useGdprStore()
const auth = useAuthStore()
const { confirm } = useConfirm()
const { resolveError } = useErrorHandler()
const { toast } = useToast()

const exporting = ref(false)
const deleting = ref(false)
const showDeleteForm = ref(false)
const deletePassword = ref('')
const deleteError = ref('')

async function handleExport() {
  exporting.value = true
  try {
    const data = await gdprStore.exportMyData()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'my-data.json'
    link.click()
    URL.revokeObjectURL(url)
    toast({ title: t('gdpr.exportSuccess') })
  } catch (err) {
    toast({ title: resolveError(err), variant: 'destructive' })
  } finally {
    exporting.value = false
  }
}

function cancelDelete() {
  showDeleteForm.value = false
  deletePassword.value = ''
  deleteError.value = ''
}

async function handleDelete() {
  const ok = await confirm(
    t('gdpr.deleteConfirmTitle'),
    t('gdpr.deleteConfirmDescription'),
    t('gdpr.deleteConfirm'),
    'destructive',
  )
  if (!ok) return

  deleting.value = true
  deleteError.value = ''
  try {
    await gdprStore.deleteMyAccount({ current_password: deletePassword.value })
    await auth.logout()
    router.push('/login')
  } catch (err) {
    deleteError.value = resolveError(err)
  } finally {
    deleting.value = false
  }
}
</script>
