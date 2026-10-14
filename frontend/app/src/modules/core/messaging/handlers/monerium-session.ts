import type { MessageHandler } from '../interfaces';
import type { MoneriumSessionKeyExpiredData } from '@/modules/core/messaging/types';
import { NotificationCategory, NotificationGroup, Severity } from '@rotki/common';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { useMoneriumOAuth } from '@/modules/integrations/monerium/use-monerium-auth';
import { signInReminderGroup } from '@/modules/integrations/use-integration-sign-in-reminder';

export function createMoneriumSessionHandler(
  t: ReturnType<typeof useI18n>['t'],
  router: ReturnType<typeof useRouter>,
): MessageHandler<MoneriumSessionKeyExpiredData> {
  const { refreshStatus, setStatus } = useMoneriumOAuth();

  return createNotificationHandler<MoneriumSessionKeyExpiredData>(async (data) => {
    const notConnected = data.reason === 'not_connected';
    if (!data.reminder) {
      // Backend may have cleared credentials (invalid_grant); update UI state immediately.
      // A reminder is sent while already signed out, so there is no state to update.
      setStatus({ authenticated: false });
      await refreshStatus();
    }

    return {
      action: {
        action: async () => router.push({
          name: '/api-keys/external/',
          query: { service: 'monerium' },
        }),
        icon: 'lu-arrow-right',
        label: notConnected ? t('external_services.actions.authenticate') : t('external_services.actions.reauthenticate'),
        persist: true,
      },
      category: NotificationCategory.DEFAULT,
      display: true,
      // A reminder repeats on every redecode that finds events to enrich, so it is nagged on a
      // schedule. The expiry itself is a change the user should hear about at once.
      group: data.reminder ? signInReminderGroup('monerium') : NotificationGroup.MONERIUM_AUTH,
      message: data.error,
      severity: Severity.WARNING,
      title: notConnected
        ? t('notification_messages.monerium_not_connected.title')
        : t('notification_messages.monerium_session_key_expired.title'),
    };
  });
}
