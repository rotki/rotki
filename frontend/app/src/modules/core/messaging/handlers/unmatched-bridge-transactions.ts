import type { Router } from 'vue-router';
import type { MessageHandler } from '../interfaces';
import type { UnmatchedBridgeTransactionsData } from '@/modules/core/messaging/types';
import {
  type Notification,
  NotificationCategory,
  NotificationGroup,
  Priority,
  Severity,
} from '@rotki/common';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

export function createUnmatchedBridgeTransactionsHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: Pick<Router, 'currentRoute' | 'push'>,
): MessageHandler<UnmatchedBridgeTransactionsData> {
  const { removeMatching } = useNotifications();

  return {
    async handle(data: UnmatchedBridgeTransactionsData): Promise<Notification | null> {
      removeMatching(
        notification => notification.group === NotificationGroup.UNMATCHED_BRIDGE_TRANSACTIONS,
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
              query: { openMatchBridgesDialog: 'true' },
            }),
          label: t('notification_messages.unmatched_bridge_transactions.action'),
          persist: true,
        },
        category: NotificationCategory.DEFAULT,
        display: true,
        group: NotificationGroup.UNMATCHED_BRIDGE_TRANSACTIONS,
        message: t('notification_messages.unmatched_bridge_transactions.message', {
          count: data.count,
        }),
        priority: Priority.ACTION,
        severity: Severity.WARNING,
        title: t('notification_messages.unmatched_bridge_transactions.title', data.count),
      };
    },
  };
}
