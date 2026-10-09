import type { UseNotificationCooldownReturn } from '../use-notification-cooldown';
import type { NotificationStrategy, NotificationStrategyContext } from './types';
import { NotificationGroup, NotificationKind, Severity } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createNotification } from '@/modules/core/notifications/notification-utils';
import { createGroupUpdateStrategy } from './group-update';

const RESULT = NotificationKind.RESULT;

describe('createGroupUpdateStrategy', () => {
  const group = NotificationGroup.BEACONCHAIN_RATE_LIMITED;

  let cooldown: UseNotificationCooldownReturn;
  let strategy: NotificationStrategy;

  beforeEach(() => {
    cooldown = {
      recordDisplay: vi.fn(),
      shouldSuppress: vi.fn(() => false),
    };
    strategy = createGroupUpdateStrategy(cooldown);
  });

  function context(notifications: NotificationStrategyContext['notifications'] = []): NotificationStrategyContext {
    return { getNextId: () => 99, notifications };
  }

  it('should skip a notification that belongs to no group', () => {
    const result = strategy.process({ kind: RESULT, message: 'test', severity: Severity.INFO, title: 'test' }, context());

    expect(result).toBeUndefined();
    expect(cooldown.shouldSuppress).not.toHaveBeenCalled();
  });

  it('should show a new group notification that is not suppressed', () => {
    const result = strategy.process({ group, kind: NotificationKind.ANNOUNCEMENT, message: 'no indexers', severity: Severity.INFO, title: 'test' }, context());

    expect(result!.notifications).toHaveLength(1);
    expect(result!.notifications[0].display).toBe(true);
    expect(cooldown.recordDisplay).toHaveBeenCalledWith(group);
  });

  it('should still create a suppressed group notification, without displaying it', () => {
    vi.mocked(cooldown.shouldSuppress).mockReturnValue(true);

    const result = strategy.process({ group, kind: RESULT, message: 'no indexers', severity: Severity.INFO, title: 'test' }, context());

    // Exhausted is not gone: the row stays in the sidebar, actionable, it just does not interrupt.
    expect(result!.notifications).toHaveLength(1);
    expect(result!.notifications[0].display).toBe(false);
    expect(result!.notifications[0].group).toBe(group);
    expect(result!.notifications[0].message).toBe('no indexers');
  });

  it('should not record a display for a notification that was never displayed', () => {
    vi.mocked(cooldown.shouldSuppress).mockReturnValue(true);

    strategy.process({ group, kind: RESULT, message: 'no indexers', severity: Severity.INFO, title: 'test' }, context());

    expect(cooldown.recordDisplay).not.toHaveBeenCalled();
  });

  it('should not record a display for a new notification whose kind does not pop', () => {
    const result = strategy.process(
      { group, kind: NotificationKind.FAILURE, message: 'no indexers', severity: Severity.INFO, title: 'test' },
      context(),
    );

    expect(result!.notifications[0].display).toBe(false);
    expect(cooldown.recordDisplay).not.toHaveBeenCalled();
  });

  it('should store the kind of the update it decided display from', () => {
    const existing = [createNotification(2, { group, kind: RESULT, message: 'stale', severity: Severity.INFO, title: 'test' })];

    const result = strategy.process({ group, kind: NotificationKind.FAILURE, message: 'fresh', severity: Severity.INFO, title: 'test' }, context(existing));

    expect(result!.notifications[0].kind).toBe(NotificationKind.FAILURE);
    expect(result!.notifications[0].display).toBe(false);
  });

  it('should keep separate groups apart', () => {
    const other = NotificationGroup.NEW_DETECTED_TOKENS;
    const existing = [createNotification(1, { group, kind: RESULT, message: 'optimism', severity: Severity.INFO, title: 'test' })];

    const result = strategy.process({ group: other, kind: RESULT, message: 'binance', severity: Severity.INFO, title: 'test' }, context(existing));

    expect(result!.notifications).toHaveLength(2);
    expect(result!.notifications.map(({ group }) => group)).toStrictEqual([group, other]);
  });

  it('should refresh an existing notification and move it to the top', () => {
    const existing = [
      createNotification(1, { group: NotificationGroup.NEW_DETECTED_TOKENS, kind: RESULT, message: 'other', severity: Severity.INFO, title: 'other' }),
      createNotification(2, { group, kind: RESULT, message: 'stale', severity: Severity.INFO, title: 'test' }),
    ];

    const result = strategy.process(
      { group, groupCount: 3, kind: NotificationKind.ANNOUNCEMENT, message: 'fresh', severity: Severity.WARNING, title: 'test' },
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
    const existing = [createNotification(2, { group, groupCount: 1, kind: RESULT, message: 'stale', severity: Severity.INFO, title: 'test' })];
    const originalDate = existing[0].date;

    const result = strategy.process(
      { group, groupCount: 5, kind: RESULT, message: 'fresh', severity: Severity.INFO, title: 'test' },
      context(existing),
    );

    // The content is kept current, but the untouched date keeps it from jumping the sidebar order.
    expect(result!.notifications[0]).toMatchObject({ display: false, groupCount: 5, message: 'fresh' });
    expect(result!.notifications[0].date).toBe(originalDate);
    expect(cooldown.recordDisplay).not.toHaveBeenCalled();
  });

  it('should take the severity of the update over the one the row had', () => {
    const existing = [createNotification(2, { group, kind: RESULT, message: 'stale', severity: Severity.WARNING, title: 'test' })];

    const result = strategy.process({ group, kind: RESULT, message: 'fresh', severity: Severity.ERROR, title: 'test' }, context(existing));

    expect(result!.notifications[0].severity).toBe(Severity.ERROR);
  });

  it('should consult the cooldown once per payload', () => {
    strategy.process({ group, kind: RESULT, message: 'no indexers', severity: Severity.INFO, title: 'test' }, context());

    expect(cooldown.shouldSuppress).toHaveBeenCalledTimes(1);
  });
});
