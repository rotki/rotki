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

  it('keeps a chain refreshing until every overlapping operation finishes', () => {
    const store = useBalanceRefreshState();
    store.start('eth');
    store.start('eth');
    store.stop('eth');
    expect(store.refreshingChains.has('eth')).toBe(true);
    store.stop('eth');
    expect(store.refreshingChains.has('eth')).toBe(false);
  });

  it('serializes same-chain work while allowing another chain to proceed', async () => {
    const store = useBalanceRefreshState();
    let release!: () => void;
    let reportStarted!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const started = new Promise<void>((resolve) => {
      reportStarted = resolve;
    });
    const order: string[] = [];
    const first = store.enqueue('eth', async () => {
      order.push('first');
      reportStarted();
      await gate;
    });
    await started;
    const second = store.enqueue('eth', async () => {
      order.push('second');
    });
    await store.enqueue('btc', async () => {
      order.push('btc');
    });
    expect(order).toEqual(['first', 'btc']);
    expect(store.refreshingChains.has('eth')).toBe(true);
    release();
    await Promise.all([first, second]);
    expect(order).toEqual(['first', 'btc', 'second']);
    expect(store.refreshingChains.has('eth')).toBe(false);
  });

  it('retains pending addresses until their own revision and target are queried', () => {
    const store = useBalanceRefreshState();
    store.markPending('btc', 'A', 1);
    store.markPending('btc', 'B', 2);
    store.settlePending('btc', 2, ['a']);
    expect(store.isPending('btc', 'a')).toBe(false);
    expect(store.isPending('btc', 'b')).toBe(true);
    store.settlePending('btc', 1, ['b']);
    expect(store.isPending('btc', 'b')).toBe(true);
    store.settlePending('btc', 2, []);
    expect(store.isPending('btc', 'b')).toBe(true);
    store.settlePending('btc', 2, ['b']);
    expect(store.isPending('btc', 'b')).toBe(false);
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
