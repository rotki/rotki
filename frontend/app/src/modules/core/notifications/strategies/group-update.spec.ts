import type { UseNotificationCooldownReturn } from '../use-notification-cooldown';
import type { NotificationStrategy, NotificationStrategyContext } from './types';
import { NotificationGroup, Severity } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createNotification } from '@/modules/core/notifications/notification-utils';
import { createGroupUpdateStrategy } from './group-update';

describe('createGroupUpdateStrategy', () => {
  const group = `${NotificationGroup.NO_AVAILABLE_INDEXERS}:optimism`;

  let cooldown: UseNotificationCooldownReturn;
  let strategy: NotificationStrategy;

  beforeEach(() => {
    cooldown = {
      recordDisplay: vi.fn(),
      resetSchedule: vi.fn(),
      shouldSuppress: vi.fn(() => false),
    };
    strategy = createGroupUpdateStrategy(cooldown);
  });

  function context(notifications: NotificationStrategyContext['notifications'] = []): NotificationStrategyContext {
    return { getNextId: () => 99, notifications };
  }

  it('should skip a notification that belongs to no group', () => {
    const result = strategy.process({ display: true, message: 'test', title: 'test' }, context());

    expect(result).toBeUndefined();
    expect(cooldown.shouldSuppress).not.toHaveBeenCalled();
  });

  it('should show a new group notification that is not suppressed', () => {
    const result = strategy.process({ display: true, group, message: 'no indexers', title: 'test' }, context());

    expect(result!.notifications).toHaveLength(1);
    expect(result!.notifications[0].display).toBe(true);
    expect(cooldown.recordDisplay).toHaveBeenCalledWith(group);
  });

  it('should still create a suppressed group notification, without displaying it', () => {
    vi.mocked(cooldown.shouldSuppress).mockReturnValue(true);

    const result = strategy.process({ display: true, group, message: 'no indexers', title: 'test' }, context());

    // Exhausted is not gone: the row stays in the sidebar, actionable, it just does not interrupt.
    expect(result!.notifications).toHaveLength(1);
    expect(result!.notifications[0].display).toBe(false);
    expect(result!.notifications[0].group).toBe(group);
    expect(result!.notifications[0].message).toBe('no indexers');
  });

  it('should not record a display for a notification that was never displayed', () => {
    vi.mocked(cooldown.shouldSuppress).mockReturnValue(true);

    strategy.process({ display: true, group, message: 'no indexers', title: 'test' }, context());

    expect(cooldown.recordDisplay).not.toHaveBeenCalled();
  });

  it('should not record a display for a new notification that never asked to be displayed', () => {
    const result = strategy.process({ group, message: 'no indexers', title: 'test' }, context());

    expect(result!.notifications[0].display).toBe(false);
    expect(cooldown.recordDisplay).not.toHaveBeenCalled();
  });

  it('should keep separate subjects of the same group apart', () => {
    const other = `${NotificationGroup.NO_AVAILABLE_INDEXERS}:binance_sc`;
    const existing = [createNotification(1, { display: true, group, message: 'optimism', title: 'test' })];

    const result = strategy.process({ display: true, group: other, message: 'binance', title: 'test' }, context(existing));

    expect(result!.notifications).toHaveLength(2);
    expect(result!.notifications.map(({ group }) => group)).toStrictEqual([group, other]);
  });

  it('should refresh an existing notification and move it to the top', () => {
    const existing = [
      createNotification(1, { group: NotificationGroup.NEW_DETECTED_TOKENS, message: 'other', title: 'other' }),
      createNotification(2, { display: true, group, message: 'stale', title: 'test' }),
    ];

    const result = strategy.process(
      { display: true, group, groupCount: 3, message: 'fresh', severity: Severity.WARNING, title: 'test' },
      context(existing),
    );

    expect(result!.notifications).toHaveLength(2);
    expect(result!.notifications[0]).toMatchObject({
      display: true,
      groupCount: 3,
      id: 2,
      message: 'fresh',
      severity: Severity.WARNING,
    });
  });

  it('should update a suppressed existing notification without displaying it again', () => {
    vi.mocked(cooldown.shouldSuppress).mockReturnValue(true);
    const existing = [createNotification(2, { display: true, group, groupCount: 1, message: 'stale', title: 'test' })];
    const originalDate = existing[0].date;

    const result = strategy.process(
      { display: true, group, groupCount: 5, message: 'fresh', title: 'test' },
      context(existing),
    );

    // The content is kept current, but the untouched date keeps it from jumping the sidebar order.
    expect(result!.notifications[0]).toMatchObject({ display: false, groupCount: 5, message: 'fresh' });
    expect(result!.notifications[0].date).toBe(originalDate);
    expect(cooldown.recordDisplay).not.toHaveBeenCalled();
  });

  it('should keep the existing severity when the payload omits it', () => {
    const existing = [createNotification(2, { group, message: 'stale', severity: Severity.ERROR, title: 'test' })];

    const result = strategy.process({ group, message: 'fresh', title: 'test' }, context(existing));

    expect(result!.notifications[0].severity).toBe(Severity.ERROR);
  });

  it('should consult the cooldown once per payload', () => {
    strategy.process({ display: true, group, message: 'no indexers', title: 'test' }, context());

    expect(cooldown.shouldSuppress).toHaveBeenCalledTimes(1);
  });
});
