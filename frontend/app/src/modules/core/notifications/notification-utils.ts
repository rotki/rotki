import {
  NotificationCategory,
  type NotificationData,
  type NotificationPayload,
  type SemiPartial,
  Severity,
} from '@rotki/common';
import { DEFAULT_PRIORITY, displaysFor } from '@/modules/core/notifications/notification-display-policy';

/**
 * Builds the stored notification a payload becomes.
 *
 * @remarks
 * Called with no payload it is the empty placeholder `NotificationPopup` holds while nothing is
 * showing, which is why the default carries `display: false`. Without it the placeholder would
 * inherit the default priority, pop as a blank toast, and block the queue it is supposed to drain.
 */
export function createNotification(
  id = 0,
  {
    action,
    category = NotificationCategory.DEFAULT,
    display,
    duration,
    extras,
    group,
    groupCount,
    i18nParam,
    message = '',
    priority = DEFAULT_PRIORITY,
    severity = Severity.INFO,
    title = '',
  }: SemiPartial<NotificationPayload, 'title' | 'message'> = {
    category: NotificationCategory.DEFAULT,
    display: false,
    message: '',
    severity: Severity.INFO,
    title: '',
  },
): NotificationData {
  return {
    action,
    category,
    date: new Date(),
    display: display ?? displaysFor(priority),
    duration: duration ?? 5000,
    extras,
    group,
    groupCount,
    i18nParam,
    id,
    message,
    priority,
    read: false,
    severity,
    title,
  };
}
