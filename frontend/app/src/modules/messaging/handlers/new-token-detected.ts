import type { MessageHandler } from '../interfaces';
import type { NewDetectedToken } from '../types/business-types';
import { NotificationCategory, NotificationGroup, Priority, Severity } from '@rotki/common';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { createStateWithNotificationHandler } from '@/modules/messaging/utils';
import { Routes } from '@/router/routes';
import { useNotificationsStore } from '@/store/notifications';

export function createNewTokenDetectedHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<NewDetectedToken> {
  return createStateWithNotificationHandler<NewDetectedToken, number>(
    async (data: NewDetectedToken) => {
      const { addNewDetectedToken } = useNewlyDetectedTokens();
      const notificationsStore = useNotificationsStore();
      const { data: notifications } = storeToRefs(notificationsStore);

      const existingNotification = get(notifications).find(({ group }) => group === NotificationGroup.NEW_DETECTED_TOKENS);
      const countAdded = addNewDetectedToken(data);
      return (existingNotification?.groupCount || 0) + +countAdded;
    },
    async (data: NewDetectedToken, count: number) => {
      if (count === 0)
        return null;

      return {
        action: {
          action: async () => router.push(Routes.ASSET_MANAGER_NEWLY_DETECTED),
          label: t('notification_messages.new_detected_token.action'),
        },
        category: NotificationCategory.DEFAULT,
        display: true,
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        groupCount: count,
        message: t(
          'notification_messages.new_detected_token.message',
          {
            count,
            identifier: data.tokenIdentifier,
          },
          count,
        ),
        priority: Priority.ACTION,
        severity: Severity.INFO,
        title: t('notification_messages.new_detected_token.title', count),
      };
    },
  );
}
