import type { NotificationHandler } from '../interfaces';
import type { UnmatchedAssetMovementsData } from '@/modules/messaging/types';
import { type Notification, NotificationCategory, NotificationGroup, Priority, Severity } from '@rotki/common';
import { Routes } from '@/router/routes';
import { useNotificationsStore } from '@/store/notifications';

export function createUnmatchedAssetMovementsHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<UnmatchedAssetMovementsData> {
  const { removeMatching } = useNotificationsStore();

  return {
    async handle(data: UnmatchedAssetMovementsData): Promise<Notification> {
      removeMatching(notification => notification.group === NotificationGroup.UNMATCHED_ASSET_MOVEMENTS);

      if (data.count === 0) {
        return {
          display: false,
          message: '',
          title: '',
        };
      }

      return {
        action: {
          action: async () => router.push({
            path: Routes.HISTORY.toString(),
          }),
          label: t('notification_messages.unmatched_asset_movements.action'),
          persist: true,
        },
        category: NotificationCategory.DEFAULT,
        display: true,
        group: NotificationGroup.UNMATCHED_ASSET_MOVEMENTS,
        message: t('notification_messages.unmatched_asset_movements.message', { count: data.count }),
        priority: Priority.ACTION,
        severity: Severity.WARNING,
        title: t('notification_messages.unmatched_asset_movements.title', data.count),
      };
    },
  };
}
