import type { NegativeBalanceDetectedData } from '@/modules/core/messaging/types/status-types';
import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useHistoricalBalancesStore } from './use-historical-balances-store';

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
