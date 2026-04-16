import { NotificationGroup, Priority, Severity } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { createNotification } from '@/modules/notifications/notification-utils';
import { createDeserializationErrorStrategy } from './deserialization-error';

function mockT(key: string, params?: Record<string, unknown>): string {
  return params ? `${key}::${JSON.stringify(params)}` : key;
}

describe('createDeserializationErrorStrategy', () => {
  const strategy = createDeserializationErrorStrategy(mockT as any);

  it('should skip non-deserialization messages', () => {
    const result = strategy.process(
      { message: 'something else', priority: Priority.BULK, severity: Severity.WARNING, title: 'test' },
      { getNextId: () => 1, notifications: [] },
    );

    expect(result).toBeUndefined();
  });

  it('should skip non-bulk deserialization messages', () => {
    const result = strategy.process(
      { message: 'Could not deserialize asset X', severity: Severity.WARNING, title: 'test' },
      { getNextId: () => 1, notifications: [] },
    );

    expect(result).toBeUndefined();
  });

  it('should create a grouped notification for first deserialization error', () => {
    const result = strategy.process(
      { message: 'Could not deserialize asset X', priority: Priority.BULK, severity: Severity.WARNING, title: 'backend' },
      { getNextId: () => 1, notifications: [] },
    );

    expect(result).toBeDefined();
    expect(result!.notifications).toHaveLength(1);
    expect(result!.notifications[0]).toMatchObject({
      group: NotificationGroup.DESERIALIZATION_ERROR,
      groupCount: 1,
    });
  });

  it('should increment count on subsequent deserialization errors', () => {
    const existing = [
      createNotification(1, {
        group: NotificationGroup.DESERIALIZATION_ERROR,
        groupCount: 3,
        message: 'old message',
        priority: Priority.BULK,
        title: 'backend',
      }),
    ];

    const result = strategy.process(
      { message: 'Could not deserialize asset Y', priority: Priority.BULK, severity: Severity.WARNING, title: 'backend' },
      { getNextId: vi.fn(), notifications: existing },
    );

    expect(result).toBeDefined();
    expect(result!.notifications).toHaveLength(1);
    expect(result!.notifications[0]).toMatchObject({
      group: NotificationGroup.DESERIALIZATION_ERROR,
      groupCount: 4,
    });
  });
});
