import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';

describe('useHistoricalBalanceProcessingStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should start with no completed processing', () => {
    const store = useHistoricalBalanceProcessingStore();

    expect(get(store.historicalBalanceProcessingCompleted)).toBe(0);
  });

  it('should count every completed processing run', () => {
    const store = useHistoricalBalanceProcessingStore();

    store.notifyHistoricalBalanceProcessingCompleted();
    store.notifyHistoricalBalanceProcessingCompleted();

    expect(get(store.historicalBalanceProcessingCompleted)).toBe(2);
  });

  it('should count completed current balance detections apart from processing runs', () => {
    const store = useHistoricalBalanceProcessingStore();

    store.notifyCurrentBalanceDetectionCompleted();

    expect(get(store.currentBalanceDetectionCompleted)).toBe(1);
    expect(get(store.historicalBalanceProcessingCompleted)).toBe(0);
  });
});
