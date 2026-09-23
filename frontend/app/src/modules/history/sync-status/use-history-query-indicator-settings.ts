import type { Ref } from 'vue';
import { useSetting } from '@/modules/settings/use-setting';

interface UseHistoryQueryIndicatorThreshold {
  minOutOfSyncPeriodMs: Readonly<Ref<number, number>>;
}

export function useHistoryQueryIndicatorSettings(): UseHistoryQueryIndicatorThreshold {
  const evmQueryIndicatorMinOutOfSyncPeriod = useSetting('evmQueryIndicatorMinOutOfSyncPeriod');
  const HOUR_IN_MS = 60 * 60 * 1000;

  const evmQueryIndicatorMinOutOfSyncPeriodMs = computed<number>(() =>
    get(evmQueryIndicatorMinOutOfSyncPeriod) * HOUR_IN_MS,
  );

  return {
    minOutOfSyncPeriodMs: evmQueryIndicatorMinOutOfSyncPeriodMs,
  };
}
