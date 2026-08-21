import type { UseNotificationCooldownReturn } from '@/modules/core/notifications/use-notification-cooldown';
import { NotificationGroup } from '@rotki/common';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { mockUpdateFrontendSetting, mockWarn } = vi.hoisted(() => ({
  mockUpdateFrontendSetting: vi.fn(),
  mockWarn: vi.fn(),
}));

vi.mock('@/modules/core/common/logging/logging', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/common/logging/logging')>(),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: mockWarn },
}));

const mockSchedule = ref<Record<string, { lastShown: number; shownCount: number }>>({});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockSchedule),
}));

vi.mock('@/modules/settings/use-frontend-settings-writer', () => ({
  useFrontendSettingsWriter: vi.fn(() => ({
    updateFrontendSetting: mockUpdateFrontendSetting,
  })),
}));

const DAY = 86_400_000;
const START = new Date('2026-01-01T00:00:00.000Z').getTime();

const scheduled = `${NotificationGroup.NO_AVAILABLE_INDEXERS}:optimism`;
const unscheduled = NotificationGroup.NEW_DETECTED_TOKENS;

describe('useNotificationCooldown', () => {
  let cooldown: UseNotificationCooldownReturn;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.setSystemTime(START);
    sessionStorage.clear();
    set(mockSchedule, {});
    mockUpdateFrontendSetting.mockReset();
    mockUpdateFrontendSetting.mockResolvedValue({ success: true });
    mockWarn.mockReset();

    // The composable is shared, so each case needs a fresh module instance to get its own state.
    vi.resetModules();
    const module = await import('@/modules/core/notifications/use-notification-cooldown');
    cooldown = module.useNotificationCooldown();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /** Advance past the debounce so the pending schedule write reaches the settings mock. */
  async function flush(): Promise<void> {
    await vi.advanceTimersByTimeAsync(2500);
    await flushPromises();
  }

  it('should not suppress a group that has never been shown', () => {
    expect(cooldown.shouldSuppress(scheduled)).toBe(false);
  });

  it('should suppress a repeat within the burst cooldown', () => {
    cooldown.recordDisplay(scheduled);

    vi.setSystemTime(START + 30_000);

    expect(cooldown.shouldSuppress(scheduled)).toBe(true);
  });

  it('should not suppress a step of a flow the user just started', () => {
    // Monerium's steps replace each other, so the second one is the outcome of the first, not a
    // repeat of it: suppressing it would leave the user with "opening browser" and no result.
    cooldown.recordDisplay(NotificationGroup.MONERIUM_AUTH);

    vi.setSystemTime(START + 5000);

    expect(cooldown.shouldSuppress(NotificationGroup.MONERIUM_AUTH)).toBe(false);
  });

  it('should suppress a scheduled group for 24 hours after the first display', () => {
    cooldown.recordDisplay(scheduled);

    vi.setSystemTime(START + DAY - 1000);
    expect(cooldown.shouldSuppress(scheduled)).toBe(true);

    vi.setSystemTime(START + DAY);
    expect(cooldown.shouldSuppress(scheduled)).toBe(false);
  });

  it('should widen the interval to 48 hours after the second display', () => {
    set(mockSchedule, { [scheduled]: { lastShown: START, shownCount: 2 } });

    vi.setSystemTime(START + 2 * DAY - 1000);
    expect(cooldown.shouldSuppress(scheduled)).toBe(true);

    vi.setSystemTime(START + 2 * DAY);
    expect(cooldown.shouldSuppress(scheduled)).toBe(false);
  });

  it('should widen the interval to 7 days after the third display', () => {
    set(mockSchedule, { [scheduled]: { lastShown: START, shownCount: 3 } });

    vi.setSystemTime(START + 7 * DAY - 1000);
    expect(cooldown.shouldSuppress(scheduled)).toBe(true);

    vi.setSystemTime(START + 7 * DAY);
    expect(cooldown.shouldSuppress(scheduled)).toBe(false);
  });

  it('should stop toasting once the ramp is exhausted, however long it has been', () => {
    set(mockSchedule, { [scheduled]: { lastShown: START, shownCount: 4 } });

    vi.setSystemTime(START + 365 * DAY);

    expect(cooldown.shouldSuppress(scheduled)).toBe(true);
  });

  it('should persist the display count so it survives a new session', async () => {
    cooldown.recordDisplay(scheduled);
    await flush();

    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      notificationSchedule: { [scheduled]: { lastShown: START, shownCount: 1 } },
    });
  });

  it('should coalesce displays recorded together into a single write', async () => {
    cooldown.recordDisplay(`${NotificationGroup.NO_AVAILABLE_INDEXERS}:optimism`);
    cooldown.recordDisplay(`${NotificationGroup.NO_AVAILABLE_INDEXERS}:binance_sc`);
    await flush();

    expect(mockUpdateFrontendSetting).toHaveBeenCalledTimes(1);
    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      notificationSchedule: {
        [`${NotificationGroup.NO_AVAILABLE_INDEXERS}:binance_sc`]: { lastShown: START, shownCount: 1 },
        [`${NotificationGroup.NO_AVAILABLE_INDEXERS}:optimism`]: { lastShown: START, shownCount: 1 },
      },
    });
  });

  it('should track each subject separately', () => {
    const other = `${NotificationGroup.NO_AVAILABLE_INDEXERS}:binance_sc`;
    cooldown.recordDisplay(scheduled);

    vi.setSystemTime(START + 2 * 60_000);

    expect(cooldown.shouldSuppress(scheduled)).toBe(true);
    expect(cooldown.shouldSuppress(other)).toBe(false);
  });

  it('should leave unscheduled groups on the burst cooldown alone', () => {
    cooldown.recordDisplay(unscheduled);

    vi.setSystemTime(START + 2 * 60_000);

    expect(cooldown.shouldSuppress(unscheduled)).toBe(false);
  });

  it('should not persist anything for an unscheduled group', async () => {
    cooldown.recordDisplay(unscheduled);
    await flush();

    expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should let a reset group interrupt again', async () => {
    set(mockSchedule, { [scheduled]: { lastShown: START, shownCount: 4 } });

    cooldown.resetSchedule(group => group === scheduled);
    await flushPromises();

    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ notificationSchedule: {} });

    set(mockSchedule, {});
    expect(cooldown.shouldSuppress(scheduled)).toBe(false);
  });

  it('should count a display that has not been written yet', async () => {
    set(mockSchedule, { [scheduled]: { lastShown: START - 8 * DAY, shownCount: 1 } });

    cooldown.recordDisplay(scheduled);
    vi.setSystemTime(START + 2 * DAY);
    cooldown.recordDisplay(scheduled);
    await flush();

    // Both displays land in one write, so the second has to read the count from the pending
    // entry — reading the settings blob would persist 2 twice and hand back a free ramp step.
    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      notificationSchedule: { [scheduled]: { lastShown: START + 2 * DAY, shownCount: 3 } },
    });
  });

  it('should drop a pending display when the group is reset before it is written', async () => {
    cooldown.recordDisplay(scheduled);
    cooldown.resetSchedule(group => group === scheduled);
    await flush();

    expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();

    // Past the burst cooldown the group is unscheduled again, rather than serving out the day
    // the discarded entry would have imposed.
    vi.setSystemTime(START + 2 * 60_000);
    expect(cooldown.shouldSuppress(scheduled)).toBe(false);
  });

  it('should warn instead of throwing when the schedule cannot be persisted', async () => {
    mockUpdateFrontendSetting.mockResolvedValue({ message: 'settings unreachable', success: false });

    cooldown.recordDisplay(scheduled);
    await flush();

    expect(mockWarn).toHaveBeenCalledWith(expect.stringContaining('settings unreachable'));
  });

  it('should not write when a reset matches nothing', async () => {
    set(mockSchedule, { [scheduled]: { lastShown: START, shownCount: 1 } });

    cooldown.resetSchedule(group => group === 'MISSING_API_KEY:blockscout');
    await flushPromises();

    expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
  });
});
