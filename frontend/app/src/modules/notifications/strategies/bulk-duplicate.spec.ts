import { Priority, Severity } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { createNotification } from '@/modules/notifications/notification-utils';
import { bulkDuplicateStrategy } from './bulk-duplicate';

describe('bulkDuplicateStrategy', () => {
  it('should skip non-bulk notifications', () => {
    const result = bulkDuplicateStrategy.process(
      { message: 'test', title: 'test' },
      { getNextId: () => 1, notifications: [] },
    );

    expect(result).toBeUndefined();
  });

  it('should skip bulk notifications with unique messages', () => {
    const result = bulkDuplicateStrategy.process(
      { message: 'new message', priority: Priority.BULK, severity: Severity.WARNING, title: 'test' },
      {
        getNextId: () => 1,
        notifications: [
          createNotification(1, { message: 'existing message', priority: Priority.BULK, title: 'test' }),
        ],
      },
    );

    expect(result).toBeUndefined();
  });

  it('should suppress bulk notifications with duplicate messages', () => {
    const existing = [
      createNotification(1, { message: 'duplicate', priority: Priority.BULK, title: 'test' }),
    ];

    const result = bulkDuplicateStrategy.process(
      { message: 'duplicate', priority: Priority.BULK, severity: Severity.WARNING, title: 'test' },
      { getNextId: () => 2, notifications: existing },
    );

    expect(result).toBeDefined();
    expect(result!.notifications).toHaveLength(1);
  });
});
