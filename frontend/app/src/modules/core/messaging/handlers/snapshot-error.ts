import type { NotificationHandler } from '../interfaces';
import type { BalanceSnapshotError } from '@/modules/core/messaging/types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { withRepeats } from '@/modules/core/messaging/utils/repeats';

export function createSnapshotErrorHandler(t: ReturnType<typeof useI18n>['t']): NotificationHandler<BalanceSnapshotError> {
  return createNotificationHandler<BalanceSnapshotError>((data, { count }) => ({
    category: NotificationCategory.DEFAULT,
    message: withRepeats(t, t('notification_messages.snapshot_failed.message', data), count),
    priority: Priority.NORMAL,
    severity: Severity.ERROR,
    title: t('notification_messages.snapshot_failed.title'),
  }));
}
