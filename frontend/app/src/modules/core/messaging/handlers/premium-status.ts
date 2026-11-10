import type { MessageHandler } from '../interfaces';
import type { PremiumStatusUpdateData } from '../types/shared-types';
import { type NotificationAction, NotificationCategory, Severity } from '@rotki/common';
import { externalLinks } from '@shared/external-links';
import { createStateWithNotificationHandler } from '@/modules/core/messaging/utils';
import { usePremium } from '@/modules/premium/use-premium';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

/** Builds the notification action that opens the docs on managing premium devices. */
export function createManageDevicesAction(
  t: ReturnType<typeof useI18n>['t'],
  openUrl: (url: string) => Promise<void>,
): NotificationAction {
  return {
    action: async () => openUrl(externalLinks.premiumDevices),
    icon: 'lu-external-link',
    label: t('notification_messages.premium.inactive.manage_devices'),
    persist: true,
  };
}

/**
 * Handles premium status changes pushed by the backend's periodic premium check.
 *
 * @remarks
 * The backend sends a `reason` only when the device limit of the premium plan was reached, so a
 * deactivation carrying one also offers a link to managing the registered devices.
 */
export function createPremiumStatusHandler(t: ReturnType<typeof useI18n>['t']): MessageHandler<PremiumStatusUpdateData> {
  const premium = usePremium();
  const { openUrl } = useInterop();

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
          display: true,
          message: t('notification_messages.premium.active.message'),
          severity: Severity.INFO,
          title: t('notification_messages.premium.active.title'),
        };
      }
      else if (!isPremiumActive && wasPremium) {
        return {
          ...(reason ? { action: createManageDevicesAction(t, openUrl) } : {}),
          category: NotificationCategory.DEFAULT,
          display: true,
          message: reason ?? (expired
            ? t('notification_messages.premium.inactive.expired_message')
            : t('notification_messages.premium.inactive.network_problem_message')),
          severity: Severity.ERROR,
          title: t('notification_messages.premium.inactive.title'),
        };
      }

      return null;
    },
  );
}
