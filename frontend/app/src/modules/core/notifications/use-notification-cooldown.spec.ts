import type { UseNotificationCooldownReturn } from '@/modules/core/notifications/use-notification-cooldown';
import { NotificationGroup } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const START = new Date('2026-01-01T00:00:00.000Z').getTime();

const grouped = `${NotificationGroup.ORACLE_PENALIZED}:coingecko`;

describe('useNotificationCooldown', () => {
  let cooldown: UseNotificationCooldownReturn;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.setSystemTime(START);
    sessionStorage.clear();

    // The composable is shared, so each case needs a fresh module instance to get its own state.
    vi.resetModules();
    const module = await import('@/modules/core/notifications/use-notification-cooldown');
    cooldown = module.useNotificationCooldown();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should not suppress a group that has never been shown', () => {
    expect(cooldown.shouldSuppress(grouped)).toBe(false);
  });

  it('should suppress a repeat within the burst cooldown', () => {
    cooldown.recordDisplay(grouped);

    vi.setSystemTime(START + 30_000);

    expect(cooldown.shouldSuppress(grouped)).toBe(true);
  });

  it('should let a group interrupt again once the burst cooldown has passed', () => {
    cooldown.recordDisplay(grouped);

    vi.setSystemTime(START + 60_000);

    expect(cooldown.shouldSuppress(grouped)).toBe(false);
  });

  it('should not suppress a step of a flow the user just started, whose later steps are its outcome rather than a repeat of it', () => {
    cooldown.recordDisplay(NotificationGroup.MONERIUM_AUTH);

    vi.setSystemTime(START + 5000);

    expect(cooldown.shouldSuppress(NotificationGroup.MONERIUM_AUTH)).toBe(false);
  });

  it('should track each subject separately', () => {
    cooldown.recordDisplay(grouped);

    vi.setSystemTime(START + 30_000);

    expect(cooldown.shouldSuppress(grouped)).toBe(true);
    expect(cooldown.shouldSuppress(`${NotificationGroup.ORACLE_PENALIZED}:cryptocompare`)).toBe(false);
  });
});
