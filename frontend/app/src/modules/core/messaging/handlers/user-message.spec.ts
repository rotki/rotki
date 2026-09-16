import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { describe, expect, it } from 'vitest';
import { createUserMessageHandler } from '@/modules/core/messaging/handlers/user-message';
import { createNotification } from '@/modules/core/notifications/notification-utils';

const classified = { fields: { entry: 'tag' }, key: 'local_db', subject: null };

describe('createUserMessageHandler', () => {
  it('should map an error to a bulk error notification with the backend title', async () => {
    const handler = createUserMessageHandler(mockT);

    const result = await handler.handle({ ...classified, value: 'Failed to query kraken balances', verbosity: 'error' });

    expect(result).toMatchObject({
      category: NotificationCategory.DEFAULT,
      message: 'Failed to query kraken balances',
      priority: Priority.BULK,
      severity: Severity.ERROR,
      title: 'notification_messages.backend.title',
    });
  });

  it('should map a warning to its own severity and title', async () => {
    const handler = createUserMessageHandler(mockT);

    const result = await handler.handle({ ...classified, value: 'Ignoring it.', verbosity: 'warning' });

    expect(result).toMatchObject({
      priority: Priority.BULK,
      severity: Severity.WARNING,
      title: 'notification_messages.backend.warning_title',
    });
  });

  it.each(['error', 'warning'] as const)('should leave display unset for a %s', async (verbosity) => {
    const handler = createUserMessageHandler(mockT);

    const result = await handler.handle({ ...classified, value: 'Skipping balance result.', verbosity });

    expect(result.display).toBeUndefined();
  });

  it.each(['error', 'warning'] as const)('should not reach the popup queue for a %s', async (verbosity) => {
    const handler = createUserMessageHandler(mockT);

    const result = await handler.handle({ ...classified, value: 'Check logs for details.', verbosity });

    expect(createNotification(1, result).display).toBe(false);
  });
});
