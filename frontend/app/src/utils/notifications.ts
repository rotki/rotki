import {
  NotificationCategory,
  type NotificationData,
  type NotificationPayload,
  Severity,
} from '@rotki/common';

export function createNotification(
  id = 0,
  {
    display,
    duration,
    message,
    severity,
    title,
    action,
    category,
    group,
    groupCount,
    i18nParam,
    priority,
  }: NotificationPayload = {
    title: '',
    message: '',
    severity: Severity.INFO,
    category: NotificationCategory.DEFAULT,
  },
): NotificationData {
  return {
    title,
    message,
    severity,
    display: display ?? false,
    duration: duration ?? 5000,
    id,
    date: new Date(),
    category,
    action,
    group,
    groupCount,
    i18nParam,
    priority,
  };
}
