import type { MessageHandler } from '../interfaces';
import type { PremiumStatusUpdateData } from '../types/shared-types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { createStateWithNotificationHandler } from '@/modules/core/messaging/utils';
import { readPremiumStatus } from '@/modules/premium/core/premium-status';
import { usePremium } from '@/modules/premium/use-premium';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

/**
 * Tracks premium status, which the backend reports on every hourly check while a premium key is
 * saved.
 *
 * @remarks
 * A key that does not work raises the action center's premium row, which stays until a check finds
 * it working again or the key is removed. Becoming active is an event rather than a condition, so it
 * stays a notification, and only on a change: a session that starts with working premium hears
 * nothing.
 */
export function createPremiumStatusHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<PremiumStatusUpdateData> {
  const premium = usePremium();
  const { clear, raise } = useRaisedConditionsStore();

  return createStateWithNotificationHandler<PremiumStatusUpdateData, boolean>(
    (data) => {
      const wasPremium = get(premium);
      const status = readPremiumStatus(data);
      set(premium, status.active);
      if (status.active)
        clear(({ kind }) => kind === RaisedConditionKind.PREMIUM_INACTIVE);
      else
        raise({ cause: status.cause, kind: RaisedConditionKind.PREMIUM_INACTIVE, reason: status.reason });
      return wasPremium;
    },
    (data, wasPremium) => {
      if (!data.isPremiumActive || wasPremium)
        return null;

      return {
        category: NotificationCategory.DEFAULT,
        message: t('notification_messages.premium.active.message'),
        priority: Priority.HIGH,
        severity: Severity.INFO,
        title: t('notification_messages.premium.active.title'),
      };
    },
  );
}
