import type { Ref } from 'vue';
import { useSetting } from '@/modules/settings/use-setting';

interface UseHistoryQueryIndicatorThreshold {
  dismissalThresholdMs: Readonly<Ref<number, number>>;
  minOutOfSyncPeriodMs: Readonly<Ref<number, number>>;
}

export function useHistoryQueryIndicatorSettings(): UseHistoryQueryIndicatorThreshold {
  const evmQueryIndicatorDismissalThreshold = useSetting('evmQueryIndicatorDismissalThreshold');
  const evmQueryIndicatorMinOutOfSyncPeriod = useSetting('evmQueryIndicatorMinOutOfSyncPeriod');
  const HOUR_IN_MS = 60 * 60 * 1000;

  const evmQueryIndicatorMinOutOfSyncPeriodMs = computed<number>(() =>
    get(evmQueryIndicatorMinOutOfSyncPeriod) * HOUR_IN_MS,
  );

  const evmQueryIndicatorDismissalThresholdMs = computed<number>(() =>
    get(evmQueryIndicatorDismissalThreshold) * HOUR_IN_MS,
  );

  return {
    dismissalThresholdMs: readonly(evmQueryIndicatorDismissalThresholdMs),
    minOutOfSyncPeriodMs: readonly(evmQueryIndicatorMinOutOfSyncPeriodMs),
  };
}
