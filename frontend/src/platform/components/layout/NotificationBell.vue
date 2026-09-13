<template>
  <Popover v-model:open="open">
    <PopoverTrigger as-child>
      <button
        class="relative p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        :aria-label="$t('notifications.title')"
      >
        <Bell class="w-4 h-4 transition-transform" :class="{ 'bell-ring': isRinging }" />
        <span
          v-if="store.hasUnread"
          class="absolute -top-0.5 -right-0.5 min-w-[1.1rem] h-[1.1rem] px-0.5 rounded-full bg-destructive text-destructive-foreground text-[0.6rem] font-bold leading-[1.1rem] text-center"
          >{{ store.unreadCount > 99 ? '99+' : store.unreadCount }}</span
        >
      </button>
    </PopoverTrigger>

    <PopoverContent align="end" class="w-96 p-0">
      <div class="flex items-center justify-between px-4 py-3 border-b border-border">
        <span class="font-semibold text-sm">{{ $t('notifications.title') }}</span>
        <button
          v-if="store.hasUnread"
          class="text-xs text-muted-foreground hover:text-foreground transition-colors"
          @click="store.markAllRead()"
        >
          {{ $t('notifications.markAllRead') }}
        </button>
      </div>

      <div v-if="store.isLoading" class="flex items-center justify-center py-8">
        <Loader2 class="w-5 h-5 animate-spin text-muted-foreground" />
      </div>

      <div v-else-if="store.notifications.length === 0" class="px-4 py-8 text-center">
        <p class="text-sm text-muted-foreground">{{ $t('notifications.empty') }}</p>
      </div>

      <ul v-else class="divide-y divide-border max-h-80 overflow-y-auto">
        <li
          v-for="n in store.notifications"
          :key="n.id"
          class="group px-4 py-3 flex gap-3 hover:bg-accent/50 transition-colors"
          :class="{ 'bg-primary/5': !n.read_at }"
        >
          <button class="flex-1 min-w-0 text-left" @click="handleNotificationClick(n)">
            <p class="text-sm font-medium truncate">{{ getTitle(n) }}</p>
            <p v-if="getDescription(n)" class="text-xs text-foreground/70 mt-0.5 truncate">
              {{ getDescription(n) }}
            </p>
            <p class="text-xs text-muted-foreground mt-0.5">
              {{ formatRelativeTime(n.created_at) }}
            </p>
          </button>
          <div class="shrink-0 flex items-start pt-1.5">
            <template v-if="!n.read_at">
              <button
                class="relative w-5 h-5 flex items-center justify-center rounded transition-all hover:bg-primary/10"
                :title="$t('notifications.markRead')"
                @click.stop="store.markRead(n.id)"
              >
                <span
                  class="absolute w-2 h-2 rounded-full bg-primary group-hover:opacity-0 transition-opacity"
                />
                <Check
                  stroke-width="3"
                  class="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                />
              </button>
            </template>
            <div v-else class="w-5 h-5" />
          </div>
        </li>
      </ul>
      <RouterLink
        to="/notifications"
        class="block px-4 py-2 border-t border-border text-xs text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors text-center"
        @click="open = false"
      >
        {{ $t('notifications.viewAll') }}
      </RouterLink>
    </PopoverContent>
  </Popover>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Bell, Check, Loader2 } from 'lucide-vue-next'
import { Popover, PopoverContent, PopoverTrigger } from '@/platform/components/ui/popover'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { useToast } from '@/platform/composables/useToast'
import { useNotificationsStore } from '@/platform/stores/notifications'
import { useUiStore } from '@/platform/stores/ui'
import { useNotificationPresenter } from '@/platform/composables/useNotificationPresenter'
import type { NotificationOut } from '@/platform/types/notification'

const store = useNotificationsStore()
const uiStore = useUiStore()
const router = useRouter()
const { t } = useI18n()
const { getTitle, getDescription, getRoute } = useNotificationPresenter()
const { formatRelativeTime } = useFormatDate()
const { toast } = useToast()
const isRinging = ref(false)

const open = computed({
  get: () => uiStore.notificationBellOpen,
  set: (v) => {
    uiStore.notificationBellOpen = v
  },
})

watch(open, (isOpen) => {
  if (isOpen) store.fetchNotifications()
})

onMounted(() => {
  store.onNewNotifications((delta) => {
    isRinging.value = true
    setTimeout(() => (isRinging.value = false), 700)
    toast({
      title: t('notifications.newTitle', delta),
      description: t('notifications.newDescription'),
      onClick: () => {
        uiStore.notificationBellOpen = true
      },
    })
  })
})

async function handleNotificationClick(n: NotificationOut) {
  if (!n.read_at) await store.markRead(n.id)
  const route = getRoute(n)
  if (route) {
    open.value = false
    router.push(route)
  }
}
</script>

<style scoped>
@keyframes bell-ring {
  0% {
    transform: rotate(0deg) scale(1);
  }
  15% {
    transform: rotate(20deg) scale(1.2);
  }
  30% {
    transform: rotate(-18deg) scale(1.2);
  }
  45% {
    transform: rotate(14deg) scale(1.1);
  }
  60% {
    transform: rotate(-10deg) scale(1.1);
  }
  75% {
    transform: rotate(6deg) scale(1.05);
  }
  90% {
    transform: rotate(-3deg) scale(1.05);
  }
  100% {
    transform: rotate(0deg) scale(1);
  }
}

.bell-ring {
  animation: bell-ring 0.7s ease-in-out;
  transform-origin: top center;
}
</style>
