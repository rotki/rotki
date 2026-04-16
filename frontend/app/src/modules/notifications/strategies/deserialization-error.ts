import type { NotificationStrategy } from './types';
import { assert, NotificationGroup, Priority } from '@rotki/common';
import { createNotification } from '@/modules/notifications/notification-utils';

const DESERIALIZATION_ERROR_PREFIX = 'Could not deserialize';

export function createDeserializationErrorStrategy(
  t: ReturnType<typeof useI18n>['t'],
): NotificationStrategy {
  return {
    process(payload, context): ReturnType<NotificationStrategy['process']> {
      if (payload.priority !== Priority.BULK || !payload.message.startsWith(DESERIALIZATION_ERROR_PREFIX))
        return undefined;

      const notifications = [...context.notifications];
      const index = notifications.findIndex(
        notification => notification.group === NotificationGroup.DESERIALIZATION_ERROR,
      );

      if (index >= 0) {
        const existing = notifications[index];
        assert(existing.groupCount !== undefined, 'groupCount should be defined when group is set');

        const groupCount = existing.groupCount + 1;
        notifications[index] = {
          ...existing,
          date: new Date(),
          groupCount,
          message: t('notification_messages.deserialization_error', { count: groupCount }),
        };
      }
      else {
        notifications.push(createNotification(context.getNextId(), {
          ...payload,
          group: NotificationGroup.DESERIALIZATION_ERROR,
          groupCount: 1,
          message: t('notification_messages.deserialization_error', { count: 1 }),
        }));
      }

      return { notifications };
    },
  };
}
