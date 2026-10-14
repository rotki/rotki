import { NotificationGroup, type NotificationGroupKey } from '@rotki/common';
import { useNotificationCooldown } from '@/modules/core/notifications/use-notification-cooldown';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

type SignInIntegration = 'gnosis_pay' | 'monerium';

/**
 * The group of the reminders to sign in to an integration. The backend sends one each time a
 * redecode finds events only the integration's API can enrich, so the group is on the backed
 * off notification schedule rather than interrupting the user on every redecode.
 */
export function signInReminderGroup(integration: SignInIntegration): NotificationGroupKey {
  return `${NotificationGroup.INTEGRATION_SIGN_IN_REMINDER}:${integration}`;
}

interface UseIntegrationSignInReminderReturn {
  forgetSignInReminder: (integration: SignInIntegration) => void;
}

export function useIntegrationSignInReminder(): UseIntegrationSignInReminderReturn {
  const { removeMatching } = useNotifications();
  const { resetSchedule } = useNotificationCooldown();

  /**
   * Called once the user signs in: drops the reminder, which would otherwise still offer to sign
   * in, and restarts its schedule so that a later expiry is announced straight away.
   */
  function forgetSignInReminder(integration: SignInIntegration): void {
    const group = signInReminderGroup(integration);
    removeMatching(notification => notification.group === group);
    resetSchedule(key => key === group);
  }

  return { forgetSignInReminder };
}
