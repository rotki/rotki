import type { MessageHandler } from '../interfaces';
import type { MoneriumSessionKeyExpiredData } from '@/modules/core/messaging/types';
import { NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';

export function createMoneriumSessionHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<MoneriumSessionKeyExpiredData> {
  const { refreshStatus, setStatus } = useMoneriumOAuth();

  return createNotificationHandler<MoneriumSessionKeyExpiredData>(async (data) => {
    // Backend may have cleared credentials (invalid_grant); update UI state immediately.
    setStatus({ authenticated: false });
    await refreshStatus();

    return {
      action: {
        action: async () => router.push({
          name: '/api-keys/external/',
          query: { service: 'monerium' },
        }),
        icon: 'lu-arrow-right',
        label: t('external_services.actions.reauthenticate'),
        persist: true,
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      group: NotificationGroup.MONERIUM_AUTH,
      message: data.error,
      severity: Severity.WARNING,
      title: t('notification_messages.monerium_session_key_expired.title'),
    };
  });
}
