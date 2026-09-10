import type { MessageHandler } from '../interfaces';
import type { MoneriumSessionKeyExpiredData } from '@/modules/core/messaging/types';
import { NotificationCategory, NotificationGroup, Priority, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';

/**
 * Notifies the user that the Monerium session expired and offers to reauthenticate.
 *
 * @remarks
 * The status is set to unauthenticated before the refresh rather than left to it. The backend may
 * already have dropped the credentials (`invalid_grant`), and the refresh is a round trip, so
 * without the local write the UI would keep claiming a live session for its duration.
 */
export function createMoneriumSessionHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<MoneriumSessionKeyExpiredData> {
  const { refreshStatus, setStatus } = useMoneriumOAuth();

  return createNotificationHandler<MoneriumSessionKeyExpiredData>(async (data) => {
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
      group: NotificationGroup.MONERIUM_AUTH,
      message: data.error,
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.monerium_session_key_expired.title'),
    };
  });
}
