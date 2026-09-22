<template>
  <Card>
    <CardHeader>
      <div class="flex items-center justify-between gap-4">
        <div class="space-y-1.5">
          <CardTitle class="text-base flex items-center gap-2">
            {{ $t('settings.mfa.title') }}
            <Badge v-if="enabled" variant="secondary">{{ $t('settings.mfa.enabled') }}</Badge>
          </CardTitle>
          <CardDescription>{{ $t('settings.mfa.description') }}</CardDescription>
        </div>
        <Button v-if="!enabled && !setupData" size="sm" :disabled="busy" @click="startSetup">
          <Loader2 v-if="busy" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('settings.mfa.enable') }}
        </Button>
      </div>
    </CardHeader>

    <!-- Enrollment: scan, then confirm a code -->
    <CardContent v-if="setupData" class="space-y-4">
      <ol class="text-sm text-muted-foreground list-decimal pl-5 space-y-1">
        <li>{{ $t('settings.mfa.stepScan') }}</li>
        <li>{{ $t('settings.mfa.stepConfirm') }}</li>
      </ol>
      <div class="flex flex-col sm:flex-row gap-4 items-start">
        <img
          :src="qrCode"
          :alt="$t('settings.mfa.qrAlt')"
          class="w-44 h-44 rounded-md border bg-white p-1"
        />
        <div class="space-y-2 min-w-0">
          <p class="text-xs text-muted-foreground">{{ $t('settings.mfa.manualEntry') }}</p>
          <div class="flex items-center gap-2">
            <code class="bg-muted rounded px-2 py-1 text-xs font-mono break-all select-all">
              {{ setupData.secret }}
            </code>
            <Button variant="outline" size="sm" @click="copy(setupData.secret)">
              <Copy class="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
      <form class="space-y-2 max-w-xs" @submit.prevent="confirmSetup">
        <Label for="mfa-setup-code">{{ $t('auth.mfaCode') }}</Label>
        <OtpInput
          id="mfa-setup-code"
          v-model="setupCode"
          :disabled="busy"
          autofocus
          @complete="(v: string) => ((setupCode = v), confirmSetup())"
        />
        <p v-if="setupError" class="text-xs text-destructive">{{ setupError }}</p>
        <div class="flex gap-2 pt-1">
          <Button type="submit" size="sm" :disabled="busy || setupCode.trim().length !== 6">
            <Loader2 v-if="busy" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('settings.mfa.confirm') }}
          </Button>
          <Button type="button" variant="outline" size="sm" :disabled="busy" @click="cancelSetup">
            {{ $t('common.cancel') }}
          </Button>
        </div>
      </form>
    </CardContent>

    <CardContent v-else-if="enabled" class="flex flex-wrap gap-2">
      <Button variant="outline" size="sm" @click="openRegenerate">
        {{ $t('settings.mfa.regenerateCodes') }}
      </Button>
      <Button
        variant="outline"
        size="sm"
        class="text-destructive hover:text-destructive hover:bg-destructive/10"
        @click="openDisable"
      >
        {{ $t('settings.mfa.disable') }}
      </Button>
    </CardContent>
  </Card>

  <!-- Disable: password + code -->
  <Dialog v-model:open="disableOpen">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('settings.mfa.disableTitle') }}</DialogTitle>
        <DialogDescription>{{ $t('settings.mfa.disableDescription') }}</DialogDescription>
      </DialogHeader>
      <form class="space-y-4 mt-2" @submit.prevent="confirmDisable">
        <div class="space-y-2">
          <Label for="mfa-disable-password">{{ $t('settings.currentPassword') }}</Label>
          <PasswordInput
            id="mfa-disable-password"
            v-model="disableForm.password"
            autocomplete="current-password"
            :disabled="busy"
          />
        </div>
        <div class="space-y-2">
          <Label for="mfa-disable-code">
            {{ disableUseRecovery ? $t('auth.mfaRecoveryCode') : $t('auth.mfaCode') }}
          </Label>
          <Input
            v-if="disableUseRecovery"
            id="mfa-disable-code"
            v-model="disableForm.code"
            autocomplete="off"
            placeholder="xxxxx-xxxxx"
            maxlength="11"
            class="font-mono tracking-widest"
            :disabled="busy"
          />
          <OtpInput
            v-else
            id="mfa-disable-code"
            v-model="disableForm.code"
            :disabled="busy"
            @complete="onDisableCodeComplete"
          />
          <button
            type="button"
            class="text-xs text-muted-foreground hover:text-foreground transition-colors"
            :disabled="busy"
            @click="toggleDisableRecovery"
          >
            {{
              disableUseRecovery ? $t('auth.mfaUseAuthenticator') : $t('auth.mfaUseRecoveryCode')
            }}
          </button>
        </div>
        <p v-if="dialogError" class="text-sm text-destructive">{{ dialogError }}</p>
        <DialogFooter>
          <Button type="button" variant="outline" :disabled="busy" @click="disableOpen = false">
            {{ $t('common.cancel') }}
          </Button>
          <Button
            type="submit"
            variant="destructive"
            :disabled="
              busy ||
              !disableForm.password ||
              (disableUseRecovery ? !disableForm.code.trim() : disableForm.code.length !== 6)
            "
          >
            <Loader2 v-if="busy" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('settings.mfa.disable') }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>

  <!-- Regenerate recovery codes: authenticator code -->
  <Dialog v-model:open="regenerateOpen">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('settings.mfa.regenerateCodes') }}</DialogTitle>
        <DialogDescription>{{ $t('settings.mfa.regenerateDescription') }}</DialogDescription>
      </DialogHeader>
      <form class="space-y-4 mt-2" @submit.prevent="confirmRegenerate">
        <div class="space-y-2">
          <Label for="mfa-regenerate-code">{{ $t('auth.mfaCode') }}</Label>
          <OtpInput
            id="mfa-regenerate-code"
            v-model="regenerateCode"
            :disabled="busy"
            autofocus
            @complete="(v: string) => ((regenerateCode = v), confirmRegenerate())"
          />
        </div>
        <p v-if="dialogError" class="text-sm text-destructive">{{ dialogError }}</p>
        <DialogFooter>
          <Button type="button" variant="outline" :disabled="busy" @click="regenerateOpen = false">
            {{ $t('common.cancel') }}
          </Button>
          <Button type="submit" :disabled="busy || regenerateCode.trim().length !== 6">
            <Loader2 v-if="busy" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('settings.mfa.regenerate') }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>

  <!-- Recovery codes (shown once) -->
  <Dialog v-model:open="codesOpen">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('settings.mfa.recoveryCodesTitle') }}</DialogTitle>
        <DialogDescription>{{ $t('settings.mfa.recoveryCodesWarning') }}</DialogDescription>
      </DialogHeader>
      <ul class="grid grid-cols-2 gap-2 bg-muted rounded-md p-4 font-mono text-sm mt-2">
        <li v-for="c in recoveryCodes" :key="c" class="select-all">{{ c }}</li>
      </ul>
      <DialogFooter class="mt-2 gap-2">
        <Button variant="outline" size="sm" @click="copy(recoveryCodes.join('\n'))">
          <Copy class="w-4 h-4 mr-2" />
          {{ $t('settings.mfa.copy') }}
        </Button>
        <Button variant="outline" size="sm" @click="downloadCodes">
          <Download class="w-4 h-4 mr-2" />
          {{ $t('settings.mfa.download') }}
        </Button>
        <Button size="sm" @click="codesOpen = false">{{ $t('settings.mfa.savedCodes') }}</Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Copy, Download, Loader2 } from 'lucide-vue-next'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/platform/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/platform/components/ui/dialog'
import { Badge } from '@/platform/components/ui/badge'
import { Button } from '@/platform/components/ui/button'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import PasswordInput from '@/platform/components/common/PasswordInput.vue'
import OtpInput from '@/platform/components/common/OtpInput.vue'
import { useMfaStore } from '@/platform/stores/mfa'
import { useProfileStore } from '@/platform/stores/profile'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { BRAND } from '@/brand'
import type { MfaSetupOut } from '@/platform/types'

const { t } = useI18n()
const { toast } = useToast()
const { resolveError } = useErrorHandler()
const mfaStore = useMfaStore()
const profileStore = useProfileStore()

const enabled = computed(() => profileStore.user?.mfa_enabled ?? false)
const busy = ref(false)

const setupData = ref<MfaSetupOut | null>(null)
const qrCode = ref('')
const setupCode = ref('')
const setupError = ref('')

const disableOpen = ref(false)
const disableForm = reactive({ password: '', code: '' })
const disableUseRecovery = ref(false)
const regenerateOpen = ref(false)
const regenerateCode = ref('')
const dialogError = ref('')

const codesOpen = ref(false)
const recoveryCodes = ref<string[]>([])

function showCodes(codes: string[]) {
  recoveryCodes.value = codes
  codesOpen.value = true
}

async function startSetup() {
  busy.value = true
  try {
    // Loaded on demand so the QR library stays out of the main bundle.
    const [data, { toDataURL }] = await Promise.all([mfaStore.setup(), import('qrcode')])
    qrCode.value = await toDataURL(data.otpauth_uri, { width: 352, margin: 1 })
    setupData.value = data
    setupCode.value = ''
    setupError.value = ''
  } catch (err) {
    toast({ title: resolveError(err), variant: 'destructive' })
  } finally {
    busy.value = false
  }
}

function cancelSetup() {
  setupData.value = null
  setupCode.value = ''
  setupError.value = ''
}

async function confirmSetup() {
  if (busy.value) return
  busy.value = true
  setupError.value = ''
  try {
    const codes = await mfaStore.enable(setupCode.value.trim())
    setupData.value = null
    toast({ title: t('settings.mfa.enabledToast') })
    showCodes(codes)
  } catch (err) {
    setupError.value = resolveError(err)
    setupCode.value = ''
  } finally {
    busy.value = false
  }
}

function openDisable() {
  disableForm.password = ''
  disableForm.code = ''
  disableUseRecovery.value = false
  dialogError.value = ''
  disableOpen.value = true
}

function toggleDisableRecovery() {
  disableUseRecovery.value = !disableUseRecovery.value
  disableForm.code = ''
  dialogError.value = ''
}

// Auto-submit once the code is complete, but only if the password is in too.
function onDisableCodeComplete(value: string) {
  disableForm.code = value
  if (disableForm.password) confirmDisable()
}

async function confirmDisable() {
  if (busy.value) return
  busy.value = true
  dialogError.value = ''
  try {
    await mfaStore.disable({ password: disableForm.password, code: disableForm.code.trim() })
    disableOpen.value = false
    toast({ title: t('settings.mfa.disabledToast') })
  } catch (err) {
    const e = err as { response?: { data?: { error_code?: string } } }
    dialogError.value =
      e?.response?.data?.error_code === 'login_failed'
        ? t('settings.incorrectCurrentPassword')
        : resolveError(err)
    disableForm.code = ''
  } finally {
    busy.value = false
  }
}

function openRegenerate() {
  regenerateCode.value = ''
  dialogError.value = ''
  regenerateOpen.value = true
}

async function confirmRegenerate() {
  if (busy.value) return
  busy.value = true
  dialogError.value = ''
  try {
    const codes = await mfaStore.regenerateRecoveryCodes(regenerateCode.value.trim())
    regenerateOpen.value = false
    showCodes(codes)
  } catch (err) {
    dialogError.value = resolveError(err)
    regenerateCode.value = ''
  } finally {
    busy.value = false
  }
}

async function copy(text: string) {
  await navigator.clipboard.writeText(text)
  toast({ title: t('settings.mfa.copied') })
}

function downloadCodes() {
  const blob = new Blob([recoveryCodes.value.join('\n') + '\n'], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${BRAND.name.toLowerCase().replace(/\s+/g, '-')}-recovery-codes.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>
