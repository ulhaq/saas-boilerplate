/**
 * Presenters for the example product's in-app notifications (written by the
 * backend's `notify_project_created` hook handler). Registered by the example
 * module's `setup()`.
 */
import { registerNotificationPresenter } from '@/foundation/composables/useNotificationPresenter'

type ProjectCreatedPayload = { project_name?: string; creator_name?: string }

export function registerExampleNotifications(): void {
  registerNotificationPresenter('example.project-created', {
    getTitle: (_payload, t) => t('notifications.example.projectCreated.title'),
    getDescription: (payload, t) => {
      const { project_name, creator_name } = (payload ?? {}) as ProjectCreatedPayload
      return t('notifications.example.projectCreated.description', {
        project: project_name,
        creator: creator_name,
      })
    },
    getRoute: () => '/projects',
    getAvatarSeed: (payload) => (payload as ProjectCreatedPayload | null)?.project_name ?? null,
  })
}
