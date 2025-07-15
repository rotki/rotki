import type { NewDetectedToken } from '@/types/websocket-messages';
import { type Notification, NotificationGroup, Priority, Severity } from '@rotki/common';
import { useNewlyDetectedTokens } from '@/composables/assets/newly-detected-tokens';
import { Routes } from '@/router/routes';

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
      action: {
        action: async () => router.push(Routes.ASSET_MANAGER_NEWLY_DETECTED),
        label: t('notification_messages.new_detected_token.action'),
      },
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
  };

  return { handle };
};
