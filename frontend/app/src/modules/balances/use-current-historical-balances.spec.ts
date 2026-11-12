import type { UseCurrentHistoricalBalancesReturn } from '@/modules/balances/use-current-historical-balances';
import type { CurrentHistoricalBalancesResponse } from '@/modules/history/balances/types';
import { bigNumberify } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { createCustomPinia } from '@test/utils/create-pinia';
import { flushPromises } from '@vue/test-utils';
import { get } from '@vueuse/shared';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope } from 'vue';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';

const h = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    fetchCurrentHistoricalBalances: vi.fn<() => Promise<CurrentHistoricalBalancesResponse>>(),
    triggerHistoricalBalancesProcessing: vi.fn<() => Promise<boolean>>().mockResolvedValue(true),
    syncCompleted: ref<number>(0),
  };
});

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: (): object => ({ fetchCurrentHistoricalBalances: h.fetchCurrentHistoricalBalances }),
}));
vi.mock('@/modules/history/balances/use-historical-balances', () => ({
  useHistoricalBalances: (): object => ({ triggerHistoricalBalancesProcessing: h.triggerHistoricalBalancesProcessing }),
}));
vi.mock('@/modules/core/common/feature-flags', () => ({
  isAccountingUpdateEnabled: (): boolean => true,
}));
vi.mock('@/modules/shell/sync-progress/use-sync-completed', () => ({
  useSyncCompleted: (): object => ({ syncCompleted: h.syncCompleted }),
}));

function response(asset: string, overrides: Partial<CurrentHistoricalBalancesResponse> = {}): CurrentHistoricalBalancesResponse {
  return {
    entries: [{ amount: bigNumberify('1'), asset, location: 'ethereum', locationLabel: '0xA', protocol: null }],
    processingRequired: false,
    stale: false,
    ...overrides,
  };
}

function deferred(): { promise: Promise<CurrentHistoricalBalancesResponse>; resolve: (value: CurrentHistoricalBalancesResponse) => void } {
  let resolve!: (value: CurrentHistoricalBalancesResponse) => void;
  const promise = new Promise<CurrentHistoricalBalancesResponse>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

/** `createSharedComposable` caches per module registry, so each test gets a fresh one. */
async function importModule(): Promise<typeof import('./use-current-historical-balances')> {
  vi.resetModules();
  return import('./use-current-historical-balances');
}

let scope: EffectScope;

async function create(): Promise<UseCurrentHistoricalBalancesReturn> {
  const { useCurrentHistoricalBalances } = await importModule();
  const state = scope.run(() => useCurrentHistoricalBalances());
  if (!state)
    throw new Error('composable returned undefined outside an effect scope');
  return state;
}

describe('useCurrentHistoricalBalances', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    scope = effectScope();
    h.fetchCurrentHistoricalBalances.mockReset().mockResolvedValue(response('ETH'));
    h.triggerHistoricalBalancesProcessing.mockClear();
    h.syncCompleted.value = 0;
  });

  afterEach(() => scope.stop());

  it('should not load until a snapshot is requested', async () => {
    await create();
    await flushPromises();

    expect(h.fetchCurrentHistoricalBalances).not.toHaveBeenCalled();
  });

  it('should load on request and store the snapshot', async () => {
    const { ensureLoaded } = await create();
    await ensureLoaded();
    await flushPromises();

    expect(h.fetchCurrentHistoricalBalances).toHaveBeenCalledOnce();
    const store = useHistoricalSnapshotStore();
    expect(store.entries.map(entry => entry.asset)).toEqual(['ETH']);
    expect(store.loaded).toBe(true);
  });

  it('should load once when asked twice', async () => {
    const { ensureLoaded } = await create();
    await ensureLoaded();
    await ensureLoaded();
    await flushPromises();

    expect(h.fetchCurrentHistoricalBalances).toHaveBeenCalledOnce();
  });

  it('should surface processingRequired and stale flags', async () => {
    h.fetchCurrentHistoricalBalances.mockResolvedValue(response('ETH', { processingRequired: true, stale: true }));
    const { ensureLoaded } = await create();
    await ensureLoaded();
    await flushPromises();

    const store = useHistoricalSnapshotStore();
    expect(store.processingRequired).toBe(true);
    expect(store.stale).toBe(true);
  });

  it('should auto-refresh when backend processing completes', async () => {
    const { ensureLoaded } = await create();
    await ensureLoaded();
    await flushPromises();

    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    expect(h.fetchCurrentHistoricalBalances).toHaveBeenCalledTimes(2);
  });

  it('should not refresh on processing completion before any snapshot was requested', async () => {
    await create();
    useHistoricalBalanceProcessingStore().notifyHistoricalBalanceProcessingCompleted();
    await flushPromises();

    expect(h.fetchCurrentHistoricalBalances).not.toHaveBeenCalled();
  });

  it('should drop a stale response when a newer load started', async () => {
    const slow = deferred();
    h.fetchCurrentHistoricalBalances.mockReturnValueOnce(slow.promise).mockResolvedValueOnce(response('DAI'));
    const { ensureLoaded, refresh } = await create();
    const store = useHistoricalSnapshotStore();
    startPromise(ensureLoaded());
    await flushPromises();

    // An explicit refresh overtakes the in-flight first request.
    startPromise(refresh());
    await flushPromises();
    slow.resolve(response('ETH'));
    await flushPromises();

    expect(store.entries.map(entry => entry.asset)).toEqual(['DAI']);
  });

  it('should refresh a loaded snapshot when a page sets it up again after every page left', async () => {
    const { ensureLoaded } = await create();
    await ensureLoaded();
    await flushPromises();
    scope.stop();

    h.syncCompleted.value += 1;
    await flushPromises();
    expect(h.fetchCurrentHistoricalBalances).toHaveBeenCalledOnce();

    scope = effectScope();
    const { useCurrentHistoricalBalances } = await import('./use-current-historical-balances');
    scope.run(() => useCurrentHistoricalBalances());
    await flushPromises();

    expect(h.fetchCurrentHistoricalBalances).toHaveBeenCalledTimes(2);
  });

  it('should not load on set-up when nothing has been loaded yet', async () => {
    await create();
    await flushPromises();

    expect(h.fetchCurrentHistoricalBalances).not.toHaveBeenCalled();
  });

  it('should trigger backend processing on demand', async () => {
    const { triggerProcessing } = await create();
    await triggerProcessing();

    expect(h.triggerHistoricalBalancesProcessing).toHaveBeenCalledOnce();
  });

  it('should record an error and stop loading on failure', async () => {
    h.fetchCurrentHistoricalBalances.mockRejectedValue(new Error('backend down'));
    const { ensureLoaded, loading } = await create();
    await ensureLoaded();
    await flushPromises();

    const store = useHistoricalSnapshotStore();
    expect(store.error).toBe('backend down');
    expect(get(loading)).toBe(false);
  });
});
