import type { NotificationStrategy } from './types';
import { NotificationKind } from '@rotki/common';
import { displaysFor } from '@/modules/core/notifications/notification-display-policy';

/**
 * Keeps one row for a failure that repeats word for word, moved up and dated to the latest attempt.
 *
 * @remarks
 * A background poll that keeps failing would otherwise add a row per attempt to the drawer's
 * Problems section, burying everything else while the backend is down. A notification with a group
 * is left to the group strategy.
 */
export function createFailureFoldStrategy(): NotificationStrategy {
  return {
    process(payload, { notifications }): ReturnType<NotificationStrategy['process']> {
      if (payload.kind !== NotificationKind.FAILURE || payload.group)
        return undefined;

      const repeatIndex = notifications.findIndex(({ group, kind, message, title }) =>
        kind === NotificationKind.FAILURE && !group && title === payload.title && message === payload.message);
      if (repeatIndex === -1)
        return undefined;

      const repeated = {
        ...notifications[repeatIndex],
        date: payload.date ?? new Date(),
        display: payload.display ?? displaysFor(payload.kind),
      };

      return { notifications: [repeated, ...notifications.filter((_, index) => index !== repeatIndex)] };
    },
  };
}
