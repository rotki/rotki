import { NotificationGroup, Severity } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { createNotification } from '@/modules/notifications/notification-utils';
import { createBeaconchainRateLimitStrategy } from './beaconchain-rate-limit';

function mockT(key: string, params?: Record<string, unknown>): string {
  return params ? `${key}::${JSON.stringify(params)}` : key;
}

describe('createBeaconchainRateLimitStrategy', () => {
  const strategy = createBeaconchainRateLimitStrategy(mockT as any);

  it('should skip non-beaconchain messages', () => {
    const result = strategy.process(
      { message: 'some other error', severity: Severity.WARNING, title: 'test' },
      { getNextId: () => 1, notifications: [] },
    );

    expect(result).toBeUndefined();
  });

  it('should create a grouped notification for first rate limit error', () => {
    const result = strategy.process(
      {
        message: 'Beaconcha.in is rate limited until 2025-01-15T12:00:00Z. Check logs',
        severity: Severity.WARNING,
        title: 'Endpoint 1',
      },
      { getNextId: () => 1, notifications: [] },
    );

    expect(result).toBeDefined();
    expect(result!.notifications).toHaveLength(1);
    expect(result!.notifications[0]).toMatchObject({
      group: NotificationGroup.BEACONCHAIN_RATE_LIMITED,
      groupCount: 1,
      extras: { endpoints: ['Endpoint 1'], until: '2025-01-15T12:00:00Z' },
    });
  });

  it('should group multiple endpoints together', () => {
    const existing = [
      createNotification(1, {
        extras: { endpoints: ['Endpoint 1'], until: '2025-01-15T12:00:00Z' },
        group: NotificationGroup.BEACONCHAIN_RATE_LIMITED,
        groupCount: 1,
        message: 'old message',
        title: 'grouped',
      }),
    ];

    const result = strategy.process(
      {
        message: 'Beaconcha.in is rate limited until 2025-01-15T12:00:00Z. Check logs',
        severity: Severity.WARNING,
        title: 'Endpoint 2',
      },
      { getNextId: vi.fn(), notifications: existing },
    );

    expect(result).toBeDefined();
    expect(result!.notifications[0]).toMatchObject({
      groupCount: 2,
      extras: { endpoints: ['Endpoint 1', 'Endpoint 2'] },
    });
  });

  it('should not add duplicate endpoints', () => {
    const existing = [
      createNotification(1, {
        extras: { endpoints: ['Endpoint 1'], until: '2025-01-15T12:00:00Z' },
        group: NotificationGroup.BEACONCHAIN_RATE_LIMITED,
        groupCount: 1,
        message: 'old',
        title: 'grouped',
      }),
    ];

    const result = strategy.process(
      {
        message: 'Beaconcha.in is rate limited until 2025-01-15T12:00:00Z. Check logs',
        severity: Severity.WARNING,
        title: 'Endpoint 1',
      },
      { getNextId: vi.fn(), notifications: existing },
    );

    expect(result).toBeDefined();
    expect(result!.notifications[0]).toMatchObject({
      groupCount: 1,
      extras: { endpoints: ['Endpoint 1'] },
    });
  });
});
