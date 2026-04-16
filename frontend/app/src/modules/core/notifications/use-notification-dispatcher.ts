import type { NotificationPayload, SemiPartial } from '@rotki/common';
import type { NotificationStrategy, NotificationStrategyContext } from './strategies/types';
import { createNotification } from '@/modules/core/notifications/notification-utils';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { createBeaconchainRateLimitStrategy } from './strategies/beaconchain-rate-limit';
import { bulkDuplicateStrategy } from './strategies/bulk-duplicate';
import { createDeserializationErrorStrategy } from './strategies/deserialization-error';
import { createGroupUpdateStrategy } from './strategies/group-update';
import { useNotificationCooldown } from './use-notification-cooldown';

interface UseNotificationDispatcherReturn {
  notify: (payload: SemiPartial<NotificationPayload, 'title' | 'message'>) => void;
}

export function useNotificationDispatcher(): UseNotificationDispatcherReturn {
  const { t } = useI18n({ useScope: 'global' });
  const store = useNotificationsStore();
  const cooldown = useNotificationCooldown();

  const strategies: NotificationStrategy[] = [
    bulkDuplicateStrategy,
    createDeserializationErrorStrategy(t),
    createBeaconchainRateLimitStrategy(t),
    createGroupUpdateStrategy(cooldown),
  ];

  function notify(payload: SemiPartial<NotificationPayload, 'title' | 'message'>): void {
    const context: NotificationStrategyContext = {
      getNextId: store.getNextId,
      notifications: store.trimmedCopy(),
    };

    for (const strategy of strategies) {
      const result = strategy.process(payload, context);
      if (result) {
        store.replace(result.notifications);
        return;
      }
    }

    // No strategy matched — add as a plain new notification
    store.add([createNotification(store.getNextId(), payload)]);
  }

  return { notify };
}
