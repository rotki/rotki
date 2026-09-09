import type { ComputedRef } from 'vue';
import { type NotificationData, Severity } from '@rotki/common';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

type BadgeColor = 'error' | 'warning' | 'primary';

export interface UseNotificationBadgeReturn {
  /** How many notifications only the user can resolve, or 0 when the badge is a dot or absent. */
  actionCount: ComputedRef<number>;
  /** Whether to show the badge at all. */
  visible: ComputedRef<boolean>;
  /** The badge's text: the count, or empty for the dot. */
  text: ComputedRef<string>;
  /** Severity of the worst outstanding item, or `primary` for the dot. */
  color: ComputedRef<BadgeColor>;
}

function worstSeverity(notifications: NotificationData[]): BadgeColor {
  if (notifications.some(notification => notification.severity === Severity.ERROR))
    return 'error';

  if (notifications.some(notification => notification.severity === Severity.WARNING))
    return 'warning';

  return 'primary';
}

/**
 * Drives the notification bell's badge, which carries two different signals.
 *
 * @remarks
 * A **count** means outstanding work only the user can resolve, coloured by the worst severity
 * among those items. It survives opening the drawer, because the drawer is not where a missing API
 * key gets fixed; it goes when the row does.
 *
 * A **dot** means something arrived that the user has not looked at, and clears the moment they
 * open the drawer. It carries no number on purpose: since the legacy lane went silent the drawer
 * accumulates hundreds of technical strings, and a count over those is the uninformative number
 * this badge used to show.
 */
export function useNotificationBadge(): UseNotificationBadgeReturn {
  const { actionRequired, hasUnread } = storeToRefs(useNotificationsStore());

  const actionCount = computed<number>(() => get(actionRequired).length);

  const visible = computed<boolean>(() => get(actionCount) > 0 || get(hasUnread));

  const text = computed<string>(() => {
    const count = get(actionCount);
    return count > 0 ? count.toString() : '';
  });

  const color = computed<BadgeColor>(() =>
    get(actionCount) > 0 ? worstSeverity(get(actionRequired)) : 'primary',
  );

  return { actionCount, color, text, visible };
}
