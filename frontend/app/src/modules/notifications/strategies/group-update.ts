import type { UseNotificationCooldownReturn } from '../use-notification-cooldown';
import type { NotificationStrategy } from './types';
import { createNotification } from '@/modules/notifications/notification-utils';

export function createGroupUpdateStrategy(cooldown: UseNotificationCooldownReturn): NotificationStrategy {
  return {
    process(payload, context): ReturnType<NotificationStrategy['process']> {
      const groupToFind = payload.group;
      if (!groupToFind)
        return undefined;

      const notifications = [...context.notifications];
      const existingIndex = notifications.findIndex(({ group }) => group === groupToFind);

      if (existingIndex === -1) {
        const notification = createNotification(context.getNextId(), payload);

        if (notification.display)
          cooldown.recordDisplay(groupToFind);

        notifications.push(notification);
        return { notifications };
      }

      const existing = notifications[existingIndex];
      let date = new Date();
      let display = payload.display ?? false;

      if (cooldown.shouldSuppress(groupToFind)) {
        date = existing.date;
        display = false;
      }

      const updated = {
        ...existing,
        action: payload.action,
        date,
        display,
        groupCount: payload.groupCount,
        message: payload.message,
        priority: payload.priority,
        severity: payload.severity ?? existing.severity,
        title: payload.title,
      };

      notifications.splice(existingIndex, 1);
      notifications.unshift(updated);

      return { notifications };
    },
  };
}
