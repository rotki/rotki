import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainBalanceStaleness } from '@/modules/balances/use-blockchain-balance-staleness';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';

describe('useBlockchainBalanceStaleness', () => {
  let store: ReturnType<typeof useBlockchainRefreshTimestampsStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useBlockchainRefreshTimestampsStore();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return undefined timestamp when no data exists', () => {
    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBeUndefined();
  });

  it('should return the oldest timestamp across all chains', () => {
    const now = Math.floor(Date.now() / 1000);
    store.updateTimestamps({ eth: now - 300, btc: now - 100 });

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshTimestamp)).toBe(now - 300);
  });

  it('should return timestamp for a specific chain when provided', () => {
    const now = Math.floor(Date.now() / 1000);
    store.updateTimestamps({ eth: now - 300, btc: now - 100 });

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness('btc');
    expect(get(lastRefreshTimestamp)).toBe(now - 100);
  });

  it('should return undefined for a specific chain with no data', () => {
    store.updateTimestamps({ eth: 1000 });

    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness('btc');
    expect(get(lastRefreshTimestamp)).toBeUndefined();
  });

  it('should support reactive chain parameter', () => {
    const now = Math.floor(Date.now() / 1000);
    store.updateTimestamps({ eth: now - 300, btc: now - 100 });

    const chain = ref<string | undefined>('eth');
    const { lastRefreshTimestamp } = useBlockchainBalanceStaleness(chain);
    expect(get(lastRefreshTimestamp)).toBe(now - 300);

    set(chain, 'btc');
    expect(get(lastRefreshTimestamp)).toBe(now - 100);

    set(chain, undefined);
    // When no chain specified, returns the oldest
    expect(get(lastRefreshTimestamp)).toBe(now - 300);
  });

  it('should return a non-empty lastRefreshed string when timestamps exist', () => {
    const now = Math.floor(Date.now() / 1000);
    store.updateTimestamps({ eth: now - 60 });

    const { lastRefreshed } = useBlockchainBalanceStaleness();
    expect(get(lastRefreshed)).toBeTruthy();
    expect(typeof get(lastRefreshed)).toBe('string');
  });
});
