import type { ComputedRef } from 'vue';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotificationMute } from '@/modules/core/notifications/use-notification-mute';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

interface UseNotificationUnreadReturn {
  /** Whether the drawer holds something new the user has not seen, leaving out what they muted. */
  hasUnread: ComputedRef<boolean>;
}

/**
 * What lights the unread dot on the notification button.
 *
 * @remarks
 * A muted group still lands in the drawer, under its muted section, so the stores' own unread state
 * counts it; the dot must not.
 */
export function useNotificationUnread(): UseNotificationUnreadReturn {
  const { data: notifications } = storeToRefs(useNotificationsStore());
  const { problems } = storeToRefs(useBackendProblemsStore());
  const { isNotificationMuted, isProblemMuted } = useNotificationMute();

  const hasUnread = computed<boolean>(() =>
    get(notifications).some(notification => !notification.read && !isNotificationMuted(notification))
    || get(problems).some(problem => !problem.read && !isProblemMuted(problem)));

  return { hasUnread };
}
