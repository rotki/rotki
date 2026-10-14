// Seam: once the user signs in, the reminder for that integration leaves the notification list
// and its nag schedule starts over, while the other integration's reminder is left alone.
import { type NotificationData, NotificationGroup } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { signInReminderGroup, useIntegrationSignInReminder } from '@/modules/integrations/use-integration-sign-in-reminder';

const removeMatching = vi.fn<(predicate: (n: NotificationData) => boolean) => void>();
const resetSchedule = vi.fn<(predicate: (group: string) => boolean) => void>();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockImplementation(() => ({ removeMatching })),
}));

vi.mock('@/modules/core/notifications/use-notification-cooldown', () => ({
  useNotificationCooldown: vi.fn().mockImplementation(() => ({ resetSchedule })),
}));

describe('useIntegrationSignInReminder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should key the reminder group by integration', () => {
    expect(signInReminderGroup('monerium')).toBe(`${NotificationGroup.INTEGRATION_SIGN_IN_REMINDER}:monerium`);
    expect(signInReminderGroup('gnosis_pay')).toBe(`${NotificationGroup.INTEGRATION_SIGN_IN_REMINDER}:gnosis_pay`);
  });

  it('should remove only the reminder of the integration the user signed in to', () => {
    useIntegrationSignInReminder().forgetSignInReminder('monerium');

    expect(removeMatching).toHaveBeenCalledOnce();
    const predicate = removeMatching.mock.calls[0][0];
    expect(predicate(createMock<NotificationData>({ group: signInReminderGroup('monerium') }))).toBe(true);
    expect(predicate(createMock<NotificationData>({ group: signInReminderGroup('gnosis_pay') }))).toBe(false);
    expect(predicate(createMock<NotificationData>({ group: NotificationGroup.MONERIUM_AUTH }))).toBe(false);
  });

  it('should restart only the schedule of the integration the user signed in to', () => {
    useIntegrationSignInReminder().forgetSignInReminder('gnosis_pay');

    expect(resetSchedule).toHaveBeenCalledOnce();
    const predicate = resetSchedule.mock.calls[0][0];
    expect(predicate(signInReminderGroup('gnosis_pay'))).toBe(true);
    expect(predicate(signInReminderGroup('monerium'))).toBe(false);
    expect(predicate(`${NotificationGroup.MISSING_API_KEY}:gnosis_pay`)).toBe(false);
  });
});
