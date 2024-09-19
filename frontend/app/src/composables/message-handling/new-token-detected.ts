import { type Notification, NotificationGroup, Priority, Severity } from '@rotki/common';
import { Routes } from '@/router/routes';
import type { NewDetectedToken } from '@/types/websocket-messages';

interface UseNewTokenDetectedHandler {
  handle: (data: NewDetectedToken, notifications: Notification[]) => Notification | null;
}

export function useNewTokenDetectedHandler(t: ReturnType<typeof useI18n>['t']): UseNewTokenDetectedHandler {
  const { addNewDetectedToken } = useNewlyDetectedTokens();
  const router = useRouter();

  const handle = (data: NewDetectedToken, notifications: Notification[]): Notification | null => {
    const notification = notifications.find(({ group }) => group === NotificationGroup.NEW_DETECTED_TOKENS);

    const countAdded = addNewDetectedToken(data);
    const count = (notification?.groupCount || 0) + +countAdded;

    if (count === 0)
      return null;

    return {
      title: t('notification_messages.new_detected_token.title', count),
      message: t(
        'notification_messages.new_detected_token.message',
        {
          identifier: data.tokenIdentifier,
          count,
        },
        count,
      ),
      display: true,
      severity: Severity.INFO,
      priority: Priority.ACTION,
      action: {
        label: t('notification_messages.new_detected_token.action'),
        action: async () => await router.push(Routes.ASSET_MANAGER_NEWLY_DETECTED),
      },
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: count,
    };
  };

  return { handle };
};
