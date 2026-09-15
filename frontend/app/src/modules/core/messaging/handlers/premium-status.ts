import type { MessageHandler } from '../interfaces';
import type { PremiumStatusUpdateData } from '../types/shared-types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { createStateWithNotificationHandler } from '@/modules/core/messaging/utils';
import { usePremium } from '@/modules/premium/use-premium';

/**
 * Reports a change in premium status.
 *
 * @remarks
 * Only a change is reported, in either direction, so a session that starts and stays without premium
 * hears nothing. Becoming inactive is an error so it stands out in the drawer, not a warning.
 */
export function createPremiumStatusHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<PremiumStatusUpdateData> {
  const premium = usePremium();

  return createStateWithNotificationHandler<PremiumStatusUpdateData, boolean>(
    (data) => {
      const isPremium = get(premium);
      set(premium, data.isPremiumActive);
      return isPremium;
    },
    (data, wasPremium) => {
      const { expired, isPremiumActive, reason } = data;
      if (isPremiumActive && !wasPremium) {
        return {
          category: NotificationCategory.DEFAULT,
          message: t('notification_messages.premium.active.message'),
          priority: Priority.HIGH,
          severity: Severity.INFO,
          title: t('notification_messages.premium.active.title'),
        };
      }
      else if (!isPremiumActive && wasPremium) {
        return {
          category: NotificationCategory.DEFAULT,
          message: reason ?? (expired
            ? t('notification_messages.premium.inactive.expired_message')
            : t('notification_messages.premium.inactive.network_problem_message')),
          priority: Priority.HIGH,
          severity: Severity.ERROR,
          title: t('notification_messages.premium.inactive.title'),
        };
      }

      return null;
    },
  );
}
