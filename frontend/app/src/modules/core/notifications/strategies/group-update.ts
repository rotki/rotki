import type { UseNotificationCooldownReturn } from '../use-notification-cooldown';
import type { NotificationStrategy } from './types';
import { createNotification } from '@/modules/core/notifications/notification-utils';

export function createGroupUpdateStrategy(cooldown: UseNotificationCooldownReturn): NotificationStrategy {
  return {
    process(payload, context): ReturnType<NotificationStrategy['process']> {
      const groupToFind = payload.group;
      if (!groupToFind)
        return undefined;

      const notifications = [...context.notifications];
      const existingIndex = notifications.findIndex(({ group }) => group === groupToFind);
      const suppressed = cooldown.shouldSuppress(groupToFind);

      if (existingIndex === -1) {
        // Having no entry yet does not make this new to the user: the list starts empty on every
        // login, which is why an unresolved condition used to interrupt again at each one.
        const notification = createNotification(context.getNextId(), {
          ...payload,
          display: (payload.display ?? false) && !suppressed,
        });

        if (notification.display)
          cooldown.recordDisplay(groupToFind);

        notifications.push(notification);
        return { notifications };
      }

      const existing = notifications[existingIndex];
      let date = new Date();
      let display = payload.display ?? false;

      if (suppressed) {
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
