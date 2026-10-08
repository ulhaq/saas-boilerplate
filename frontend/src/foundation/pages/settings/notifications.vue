<route lang="yaml">
meta:
  breadcrumb: notificationPreferences.title
</route>

<template>
  <div class="max-w-2xl animate-fade-in">
    <PageHeader
      :title="$t('notificationPreferences.title')"
      :description="$t('notificationPreferences.description')"
    />

    <Card>
      <CardContent class="pt-6">
        <div v-if="loading" class="space-y-3">
          <Skeleton v-for="i in 3" :key="i" class="h-10 w-full" />
        </div>

        <EmptyState
          v-else-if="!draft.length"
          :icon="BellOff"
          :title="$t('notificationPreferences.emptyTitle')"
          :description="$t('notificationPreferences.emptyDescription')"
        />

        <form v-else class="space-y-4" @submit.prevent="handleSave">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-xs text-muted-foreground">
                <th class="pb-2 text-left font-medium" />
                <th class="w-20 pb-2 text-center font-medium">
                  {{ $t('notificationPreferences.inApp') }}
                </th>
                <th class="w-20 pb-2 text-center font-medium">
                  {{ $t('notificationPreferences.email') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pref in draft" :key="pref.category" class="border-t">
                <td class="py-3 pr-4">
                  <p class="font-medium">{{ categoryText(pref.category, 'title') }}</p>
                  <p class="text-xs text-muted-foreground mt-0.5">
                    {{ categoryText(pref.category, 'description') }}
                  </p>
                </td>
                <td class="py-3">
                  <Checkbox
                    v-model="pref.in_app"
                    class="mx-auto"
                    :aria-label="`${categoryText(pref.category, 'title')}: ${$t('notificationPreferences.inApp')}`"
                    :disabled="saving"
                  />
                </td>
                <td class="py-3">
                  <Checkbox
                    v-model="pref.email"
                    class="mx-auto"
                    :aria-label="`${categoryText(pref.category, 'title')}: ${$t('notificationPreferences.email')}`"
                    :title="
                      pref.email_required ? $t('notificationPreferences.emailRequired') : undefined
                    "
                    :disabled="saving || pref.email_required"
                  />
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="draft.some((p) => p.email_required)" class="text-xs text-muted-foreground">
            {{ $t('notificationPreferences.emailRequired') }}
          </p>
          <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
          <SaveButton :saving="saving" :saved="saved" :disabled="!changes.length">
            {{ $t('common.saveChanges') }}
          </SaveButton>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { BellOff } from '@lucide/vue'
import { Card, CardContent } from '@/foundation/components/ui/card'
import { Checkbox } from '@/foundation/components/ui/checkbox'
import { Skeleton } from '@/foundation/components/ui/skeleton'
import PageHeader from '@/foundation/components/common/PageHeader.vue'
import EmptyState from '@/foundation/components/common/EmptyState.vue'
import SaveButton from '@/foundation/components/common/SaveButton.vue'
import { useNotificationsStore } from '@/foundation/stores/notifications'
import { useErrorHandler } from '@/foundation/composables/useErrorHandler'
import { useFormGuard } from '@/foundation/composables/useFormGuard'
import { useSaveFeedback } from '@/foundation/composables/useSaveFeedback'
import type { NotificationPreferenceOut } from '@/foundation/types/notification'

const { t, te } = useI18n()
const store = useNotificationsStore()
const { resolveError } = useErrorHandler()
const { saving, saved, save } = useSaveFeedback()

const loading = ref(true)
const error = ref('')
// Editable copy of the saved preferences; saving sends only what changed.
const draft = ref<NotificationPreferenceOut[]>([])

const changes = computed(() =>
  draft.value
    .filter((pref) => {
      const stored = store.preferences.find((p) => p.category === pref.category)
      return !stored || stored.in_app !== pref.in_app || stored.email !== pref.email
    })
    .map(({ category, in_app, email }) => ({ category, in_app, email })),
)

useFormGuard(() => changes.value.length > 0)

/** Categories are declared by modules, which provide their copy under
 * `notificationPreferences.categories.<key>`; fall back to the raw key. */
function categoryText(category: string, field: 'title' | 'description'): string {
  const key = `notificationPreferences.categories.${category}.${field}`
  if (te(key)) return t(key)
  return field === 'title' ? category : ''
}

function resetDraft() {
  draft.value = store.preferences.map((p) => ({ ...p }))
}

onMounted(async () => {
  try {
    await store.fetchPreferences()
    resetDraft()
  } catch (err) {
    error.value = resolveError(err)
  } finally {
    loading.value = false
  }
})

async function handleSave() {
  error.value = ''
  try {
    await save(() => store.updatePreferences(changes.value))
    resetDraft()
  } catch (err) {
    error.value = resolveError(err)
  }
}
</script>
