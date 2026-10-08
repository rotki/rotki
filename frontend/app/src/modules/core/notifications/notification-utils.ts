import {
  type Notification,
  type NotificationData,
  NotificationKind,
  Severity,
} from '@rotki/common';
import { displaysFor } from '@/modules/core/notifications/notification-display-policy';

/**
 * Builds the stored notification a payload becomes.
 *
 * @remarks
 * Called with no payload it is the empty placeholder `NotificationPopup` holds while nothing is
 * showing, which is why the default carries `display: false`. Without it the placeholder would
 * pop as a blank toast and block the queue it is supposed to drain.
 */
export function createNotification(
  id = 0,
  {
    action,
    date = new Date(),
    display,
    duration,
    extras,
    group,
    groupCount,
    kind,
    message,
    severity,
    title,
  }: Notification = {
    display: false,
    kind: NotificationKind.RESULT,
    message: '',
    severity: Severity.INFO,
    title: '',
  },
): NotificationData {
  return {
    action,
    date,
    display: display ?? displaysFor(kind),
    duration: duration ?? 5000,
    extras,
    group,
    groupCount,
    id,
    kind,
    message,
    read: false,
    severity,
    title,
  };
}
