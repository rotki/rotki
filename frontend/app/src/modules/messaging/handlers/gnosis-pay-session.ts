import type { NotificationHandler } from '../interfaces';
import type { GnosisPaySessionKeyExpiredData } from '@/modules/messaging/types';
import { NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/messaging/utils';
import { Routes } from '@/router/routes';

export function createGnosisPaySessionHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): NotificationHandler<GnosisPaySessionKeyExpiredData> {
  return createNotificationHandler<GnosisPaySessionKeyExpiredData>(data => ({
    action: {
      action: async () => router.push({
        path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
        query: { service: 'gnosis_pay' },
      }),
      icon: 'lu-arrow-right',
      label: t('external_services.actions.replace_key'),
      persist: true,
    },
    category: NotificationCategory.DEFAULT,
    display: true,
    group: NotificationGroup.GNOSIS_PAY_SESSION_EXPIRED,
    message: data.error,
    severity: Severity.WARNING,
    title: t('notification_messages.gnosis_pay_session_key_expired.title'),
  }));
}
