import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryQueryIndicatorSettings } from './use-history-query-indicator-settings';

const evmQueryIndicatorMinOutOfSyncPeriod = ref<number>(0);

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => Reflect.get({ evmQueryIndicatorMinOutOfSyncPeriod }, key) ?? ref(undefined)),
}));

const HOUR_IN_MS = 60 * 60 * 1000;

describe('useHistoryQueryIndicatorSettings', () => {
  beforeEach(() => {
    set(evmQueryIndicatorMinOutOfSyncPeriod, 0);
  });

  it('should convert the min out-of-sync period from hours to milliseconds', () => {
    set(evmQueryIndicatorMinOutOfSyncPeriod, 2);
    const { minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();
    expect(get(minOutOfSyncPeriodMs)).toBe(2 * HOUR_IN_MS);
  });

  it('should react to the underlying setting changing', () => {
    const { minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();
    expect(get(minOutOfSyncPeriodMs)).toBe(0);
    set(evmQueryIndicatorMinOutOfSyncPeriod, 1);
    expect(get(minOutOfSyncPeriodMs)).toBe(HOUR_IN_MS);
  });
});
