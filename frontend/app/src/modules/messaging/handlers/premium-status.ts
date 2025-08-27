import type { MessageHandler } from '../interfaces';
import type { PremiumStatusUpdateData } from '../types/shared-types';
import { NotificationCategory, Severity } from '@rotki/common';
import { usePremium } from '@/composables/premium';
import { createStateWithNotificationHandler } from '@/modules/messaging/utils';

export function createPremiumStatusHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<PremiumStatusUpdateData> {
  return createStateWithNotificationHandler<PremiumStatusUpdateData, boolean>(
    (data) => {
      const premium = usePremium();
      const isPremium = get(premium);
      set(premium, data.isPremiumActive);
      return isPremium;
    },
    (data, wasPremium) => {
      if (data.isPremiumActive && !wasPremium) {
        return {
          category: NotificationCategory.DEFAULT,
          display: true,
          message: t('notification_messages.premium.active.message'),
          severity: Severity.INFO,
          title: t('notification_messages.premium.active.title'),
        };
      }
      else if (!data.isPremiumActive && wasPremium) {
        return {
          category: NotificationCategory.DEFAULT,
          display: true,
          message: data.expired
            ? t('notification_messages.premium.inactive.expired_message')
            : t('notification_messages.premium.inactive.network_problem_message'),
          severity: Severity.ERROR,
          title: t('notification_messages.premium.inactive.title'),
        };
      }

      return null;
    },
  );
}
