import type { Notification } from '@rotki/common';
import type { NotificationStrategy, NotificationStrategyContext } from './strategies/types';
import { logger } from '@/modules/core/common/logging/logging';
import { createNotification } from '@/modules/core/notifications/notification-utils';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { hasLiveSession } from '@/modules/core/session/session-lifecycle';
import { createBeaconchainRateLimitStrategy } from './strategies/beaconchain-rate-limit';
import { createGroupUpdateStrategy } from './strategies/group-update';
import { useNotificationCooldown } from './use-notification-cooldown';
import { useSilentNotifications } from './use-silent-notifications';

interface UseNotificationDispatcherReturn {
  notify: (payload: Notification) => void;
}

export function useNotificationDispatcher(): UseNotificationDispatcherReturn {
  const { t } = useI18n({ useScope: 'global' });
  const store = useNotificationsStore();
  const cooldown = useNotificationCooldown();
  const { silent } = useSilentNotifications();

  const strategies: NotificationStrategy[] = [
    createBeaconchainRateLimitStrategy(t),
    createGroupUpdateStrategy(cooldown),
  ];

  /**
   * Records a notification, unless no session is live.
   *
   * @remarks
   * Every notification belongs to a session: the logged-out screens render none, and nothing on
   * them raises one. One that arrives with no session live comes from session work that outlived
   * its logout (a request the gate refused, a handler that resumed late), so nobody needs to act
   * on it, and keeping it would surface it in the next session.
   */
  function notify(payload: Notification): void {
    if (!hasLiveSession()) {
      logger.debug(`dropped notification with no live session: ${payload.title}`);
      return;
    }

    const incoming: Notification = get(silent)
      ? { ...payload, display: false }
      : payload;

    const context: NotificationStrategyContext = {
      getNextId: store.getNextId,
      notifications: store.trimmedCopy(),
    };

    for (const strategy of strategies) {
      const result = strategy.process(incoming, context);
      if (result) {
        store.replace(result.notifications);
        return;
      }
    }

    // No strategy matched — add as a plain new notification
    store.add([createNotification(store.getNextId(), incoming)]);
  }

  return { notify };
}
