import type { NotificationHandler } from '../interfaces';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { type LegacyMessageData, MESSAGE_WARNING } from '../types/base';
import { createNotificationHandler } from '../utils/handler-factories';

export function createLegacyHandler(t: ReturnType<typeof useI18n>['t']): NotificationHandler<LegacyMessageData> {
  return createNotificationHandler<LegacyMessageData>(({ value, verbosity }) => ({
    category: NotificationCategory.DEFAULT,
    display: verbosity !== MESSAGE_WARNING,
    message: value,
    priority: Priority.BULK,
    severity: verbosity === MESSAGE_WARNING ? Severity.WARNING : Severity.ERROR,
    title: t('notification_messages.backend.title'),
  }));
}
