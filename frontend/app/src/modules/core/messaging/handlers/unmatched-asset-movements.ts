import type { MessageHandler } from '../interfaces';
import type { UnmatchedAssetMovementsData } from '@/modules/core/messaging/types';
import {
  type Notification,
  NotificationCategory,
  NotificationGroup,
  Priority,
  Severity,
} from '@rotki/common';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

export function createUnmatchedAssetMovementsHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<UnmatchedAssetMovementsData> {
  const { removeMatching } = useNotifications();

  return {
    async handle(data: UnmatchedAssetMovementsData): Promise<Notification | null> {
      removeMatching(
        notification => notification.group === NotificationGroup.UNMATCHED_ASSET_MOVEMENTS,
      );

      const currentName = get(router.currentRoute).name;
      if (data.count === 0 || currentName === '/history/events/') {
        return null;
      }

      return {
        action: {
          action: async () =>
            router.push({
              name: '/history/events/',
              query: { openMatchAssetMovementsDialog: 'true' },
            }),
          label: t('notification_messages.unmatched_asset_movements.action'),
          persist: true,
        },
        category: NotificationCategory.DEFAULT,
        display: true,
        group: NotificationGroup.UNMATCHED_ASSET_MOVEMENTS,
        message: t('notification_messages.unmatched_asset_movements.message', {
          count: data.count,
        }),
        priority: Priority.ACTION,
        severity: Severity.WARNING,
        title: t('notification_messages.unmatched_asset_movements.title', data.count),
      };
    },
  };
}
