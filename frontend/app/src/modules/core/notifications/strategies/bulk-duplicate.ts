import type { NotificationStrategy } from './types';
import { Priority } from '@rotki/common';

export const bulkDuplicateStrategy: NotificationStrategy = {
  process(payload, context): ReturnType<NotificationStrategy['process']> {
    if (payload.priority !== Priority.BULK)
      return undefined;

    const isDuplicate = context.notifications
      .filter(notification => notification.priority === Priority.BULK)
      .some(notification => notification.message === payload.message);

    if (!isDuplicate)
      return undefined;

    return { notifications: context.notifications };
  },
};
