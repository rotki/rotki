import type { HistoricalBalanceProcessingData, NegativeBalanceDetectedData } from '@/modules/core/messaging/types/status-types';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useHistoricalBalancesStore } from './use-historical-balances-store';

function progress(processed: number, total: number): HistoricalBalanceProcessingData {
  return { processed, total };
}

function negative(lastRunTs: number, eventIdentifier = 1): NegativeBalanceDetectedData {
  return {
    asset: 'ETH',
    balanceBefore: bigNumberify('-1'),
    bucket: { asset: 'ETH', location: 'ethereum', locationLabel: null, protocol: null },
    eventIdentifier,
    groupIdentifier: '0x1',
    lastRunTs,
  };
}

describe('useHistoricalBalancesStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should report processing state and percentage', () => {
    const store = useHistoricalBalancesStore();
    expect(get(store.isProcessing)).toBe(false);
    expect(get(store.processingPercentage)).toBe(0);

    store.setProcessingProgress(progress(25, 100));
    expect(get(store.isProcessing)).toBe(true);
    expect(get(store.processingPercentage)).toBe(25);

    store.setProcessingProgress(progress(100, 100));
    expect(get(store.isProcessing)).toBe(false);
    expect(get(store.processingPercentage)).toBe(100);
  });

  it('should treat a zero total as not processing', () => {
    const store = useHistoricalBalancesStore();
    store.setProcessingProgress(progress(0, 0));
    expect(get(store.isProcessing)).toBe(false);
    expect(get(store.processingPercentage)).toBe(0);
  });

  it('should reset negative balances when a new processing cycle starts', () => {
    const store = useHistoricalBalancesStore();
    store.setProcessingProgress(progress(50, 100));
    store.addNegativeBalance(negative(1000));
    expect(get(store.negativeBalances)).toHaveLength(1);

    // processed drops below the previous value -> new cycle -> reset
    store.setProcessingProgress(progress(10, 100));
    expect(get(store.negativeBalances)).toEqual([]);
  });

  it('should accumulate negative balances sharing a run timestamp', () => {
    const store = useHistoricalBalancesStore();
    store.addNegativeBalance(negative(1000, 1));
    store.addNegativeBalance(negative(1000, 2));
    expect(get(store.negativeBalances)).toHaveLength(2);
  });

  it('should start a fresh list when the run timestamp changes', () => {
    const store = useHistoricalBalancesStore();
    store.addNegativeBalance(negative(1000, 1));
    store.addNegativeBalance(negative(2000, 2));
    const result = get(store.negativeBalances);
    expect(result).toHaveLength(1);
    expect(result[0].lastRunTs).toBe(2000);
    expect(result[0].eventIdentifier).toBe(2);
  });
});
