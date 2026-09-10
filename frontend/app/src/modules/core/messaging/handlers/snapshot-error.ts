import type { NotificationHandler } from '../interfaces';
import type { BalanceSnapshotError } from '@/modules/core/messaging/types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';

export function createSnapshotErrorHandler(t: ReturnType<typeof useI18n>['t']): NotificationHandler<BalanceSnapshotError> {
  return createNotificationHandler<BalanceSnapshotError>(data => ({
    category: NotificationCategory.DEFAULT,
    message: t('notification_messages.snapshot_failed.message', data),
    priority: Priority.NORMAL,
    severity: Severity.ERROR,
    title: t('notification_messages.snapshot_failed.title'),
  }));
}
