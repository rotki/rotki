import type { NotificationHandler } from '../interfaces';
import type { UnmatchedAssetMovementsData } from '@/modules/messaging/types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/messaging/utils';
import { Routes } from '@/router/routes';

export function createUnmatchedAssetMovementsHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<UnmatchedAssetMovementsData> {
  return createNotificationHandler<UnmatchedAssetMovementsData>(({ count }) => ({
    action: {
      action: async () => router.push({
        path: Routes.HISTORY.toString(),
      }),
      label: t('notification_messages.unmatched_asset_movements.action'),
      persist: true,
    },
    category: NotificationCategory.DEFAULT,
    display: true,
    message: t('notification_messages.unmatched_asset_movements.message', { count }),
    priority: Priority.ACTION,
    severity: Severity.WARNING,
    title: t('notification_messages.unmatched_asset_movements.title'),
  }));
}
