import type { NotificationHandler } from '../interfaces';
import type { GnosisPaySessionKeyExpiredData } from '@/modules/core/messaging/types';
import { NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { signInReminderGroup } from '@/modules/integrations/use-integration-sign-in-reminder';

export function createGnosisPaySessionHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): NotificationHandler<GnosisPaySessionKeyExpiredData> {
  return createNotificationHandler<GnosisPaySessionKeyExpiredData>((data) => {
    const notConnected = data.reason === 'not_connected';
    return {
      action: {
        action: async () => router.push({
          name: '/api-keys/external/',
          query: { service: 'gnosis_pay' },
        }),
        icon: 'lu-arrow-right',
        label: notConnected ? t('external_services.actions.authenticate') : t('external_services.actions.reauthenticate'),
        persist: true,
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      // A reminder repeats on every redecode that finds events to enrich, so it is nagged on a
      // schedule. The expiry itself is a change the user should hear about at once.
      group: data.reminder ? signInReminderGroup('gnosis_pay') : NotificationGroup.GNOSIS_PAY_SESSION_EXPIRED,
      message: data.error,
      severity: Severity.WARNING,
      title: notConnected
        ? t('notification_messages.gnosis_pay_not_connected.title')
        : t('notification_messages.gnosis_pay_session_key_expired.title'),
    };
  });
}
