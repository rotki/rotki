import {
  NotificationCategory,
  type NotificationData,
  type NotificationPayload,
  Severity,
} from '@rotki/common';

export function createNotification(
  id = 0,
  {
    action,
    category,
    display,
    duration,
    extras,
    group,
    groupCount,
    i18nParam,
    message,
    priority,
    severity,
    title,
  }: NotificationPayload = {
    category: NotificationCategory.DEFAULT,
    message: '',
    severity: Severity.INFO,
    title: '',
  },
): NotificationData {
  return {
    action,
    category,
    date: new Date(),
    display: display ?? false,
    duration: duration ?? 5000,
    extras,
    group,
    groupCount,
    i18nParam,
    id,
    message,
    priority,
    severity,
    title,
  };
}
