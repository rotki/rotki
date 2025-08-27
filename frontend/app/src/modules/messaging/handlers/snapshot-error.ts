import type { NotificationHandler } from '../interfaces';
import type { BalanceSnapshotError } from '@/modules/messaging/types';
import { NotificationCategory, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/messaging/utils';

export function createSnapshotErrorHandler(t: ReturnType<typeof useI18n>['t']): NotificationHandler<BalanceSnapshotError> {
  return createNotificationHandler<BalanceSnapshotError>(data => ({
    category: NotificationCategory.DEFAULT,
    display: true,
    message: t('notification_messages.snapshot_failed.message', data),
    severity: Severity.ERROR,
    title: t('notification_messages.snapshot_failed.title'),
  }));
}
