import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryQueryIndicatorSettings } from './use-history-query-indicator-settings';

const evmQueryIndicatorDismissalThreshold = ref<number>(0);
const evmQueryIndicatorMinOutOfSyncPeriod = ref<number>(0);

vi.mock('@/modules/settings/use-frontend-settings-store', () => ({
  useFrontendSettingsStore: (): object => ({
    evmQueryIndicatorDismissalThreshold,
    evmQueryIndicatorMinOutOfSyncPeriod,
  }),
}));

const HOUR_IN_MS = 60 * 60 * 1000;

describe('useHistoryQueryIndicatorSettings', () => {
  beforeEach(() => {
    set(evmQueryIndicatorDismissalThreshold, 0);
    set(evmQueryIndicatorMinOutOfSyncPeriod, 0);
  });

  it('should convert the dismissal threshold from hours to milliseconds', () => {
    set(evmQueryIndicatorDismissalThreshold, 3);
    const { dismissalThresholdMs } = useHistoryQueryIndicatorSettings();
    expect(get(dismissalThresholdMs)).toBe(3 * HOUR_IN_MS);
  });

  it('should convert the min out-of-sync period from hours to milliseconds', () => {
    set(evmQueryIndicatorMinOutOfSyncPeriod, 2);
    const { minOutOfSyncPeriodMs } = useHistoryQueryIndicatorSettings();
    expect(get(minOutOfSyncPeriodMs)).toBe(2 * HOUR_IN_MS);
  });

  it('should react to the underlying setting changing', () => {
    const { dismissalThresholdMs } = useHistoryQueryIndicatorSettings();
    expect(get(dismissalThresholdMs)).toBe(0);
    set(evmQueryIndicatorDismissalThreshold, 1);
    expect(get(dismissalThresholdMs)).toBe(HOUR_IN_MS);
  });
});
