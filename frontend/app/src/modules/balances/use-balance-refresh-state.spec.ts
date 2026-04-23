import { beforeEach, describe, expect, it } from 'vitest';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';

describe('useBalanceRefreshState', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should start empty', () => {
    const store = useBalanceRefreshState();
    const { isRefreshing, refreshingChains } = storeToRefs(store);
    expect(get(refreshingChains).size).toBe(0);
    expect(get(isRefreshing)).toBe(false);
  });

  it('should flip isRefreshing when any chain is active', () => {
    const store = useBalanceRefreshState();
    const { isRefreshing } = storeToRefs(store);
    store.start('eth');
    expect(get(isRefreshing)).toBe(true);
    store.stop('eth');
    expect(get(isRefreshing)).toBe(false);
  });

  it('should track per-chain refresh state via useIsRefreshing', () => {
    const { start, stop, useIsRefreshing } = useBalanceRefreshState();

    const eth = useIsRefreshing('eth');
    const optimism = useIsRefreshing('optimism');

    start('eth');
    expect(get(eth)).toBe(true);
    expect(get(optimism)).toBe(false);

    start('optimism');
    expect(get(eth)).toBe(true);
    expect(get(optimism)).toBe(true);

    stop('eth');
    expect(get(eth)).toBe(false);
    expect(get(optimism)).toBe(true);
  });

  it('should be a no-op when stopping a chain that is not refreshing', () => {
    const store = useBalanceRefreshState();
    const { isRefreshing, refreshingChains } = storeToRefs(store);
    const before = get(refreshingChains);
    store.stop('eth');
    expect(get(refreshingChains)).toBe(before);
    expect(get(isRefreshing)).toBe(false);
  });

  it('should dedupe repeated starts for the same chain', () => {
    const store = useBalanceRefreshState();
    const { refreshingChains } = storeToRefs(store);
    store.start('eth');
    store.start('eth');
    expect(get(refreshingChains).size).toBe(1);
    store.stop('eth');
    expect(get(refreshingChains).size).toBe(0);
  });

  it('should reset all refreshing chains', () => {
    const store = useBalanceRefreshState();
    const { isRefreshing } = storeToRefs(store);
    store.start('eth');
    store.start('optimism');
    store.reset();
    expect(get(isRefreshing)).toBe(false);
  });
});
