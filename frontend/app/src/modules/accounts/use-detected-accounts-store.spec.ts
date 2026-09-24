import { beforeEach, describe, expect, it } from 'vitest';
import { createApp } from 'vue';
import { useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { resetState, StoreResetPlugin, StoreTrackPlugin } from '@/modules/shell/app/store-plugins';

describe('modules/accounts/use-detected-accounts-store', () => {
  const ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

  beforeEach(() => {
    const pinia = createPinia();
    pinia.use(StoreResetPlugin);
    pinia.use(StoreTrackPlugin);
    createApp({}).use(pinia);
    setActivePinia(pinia);
  });

  it('should match an address whatever its checksum case', () => {
    const store = useDetectedAccountsStore();

    store.record([{ address: ADDRESS, chain: 'eth' }]);

    expect(store.isDetected('eth', ADDRESS.toLowerCase())).toBe(true);
    expect(store.isDetected('optimism', ADDRESS)).toBe(false);
  });

  it('should record an account once, however often detection reports it', () => {
    const store = useDetectedAccountsStore();

    store.record([{ address: ADDRESS, chain: 'eth' }]);
    store.record([{ address: ADDRESS.toLowerCase(), chain: 'eth' }, { address: ADDRESS, chain: 'base' }]);

    expect(store.detectedChains(ADDRESS)).toEqual(['eth', 'base']);
  });

  it('should dismiss the marks of one address only', () => {
    const store = useDetectedAccountsStore();
    store.record([{ address: ADDRESS, chain: 'eth' }, { address: ADDRESS, chain: 'base' }, { address: '0xother', chain: 'eth' }]);

    store.dismiss(ADDRESS.toLowerCase());

    expect(store.detectedChains(ADDRESS)).toEqual([]);
    expect(store.isDetected('eth', '0xother')).toBe(true);
  });

  it('should keep an unfinished manual addition across a new run, and drop a finished one', () => {
    const store = useDetectedAccountsStore();
    const finished = store.startUserAddition('eth', ['0xDone']);
    store.startUserAddition('eth', ['0xOpen']);
    store.finishUserAddition(finished);

    store.beginRun();

    expect(store.wasAddedByUser({ address: '0xopen', chain: 'eth' })).toBe(true);
    expect(store.wasAddedByUser({ address: '0xdone', chain: 'eth' })).toBe(false);
  });

  it('should match a manual addition only on its own chain, unless it spans every EVM chain', () => {
    const store = useDetectedAccountsStore();
    store.startUserAddition('eth', ['0xOne']);
    store.startUserAddition(undefined, ['0xTwo']);

    expect(store.wasAddedByUser({ address: '0xone', chain: 'optimism' })).toBe(false);
    expect(store.wasAddedByUser({ address: '0xtwo', chain: 'optimism' })).toBe(true);
  });

  it('should forget every mark when the session state is reset at logout', () => {
    const store = useDetectedAccountsStore();
    store.record([{ address: ADDRESS, chain: 'eth' }]);
    store.setLastRun([{ address: ADDRESS, chain: 'eth' }]);

    resetState();

    expect(store.isDetected('eth', ADDRESS)).toBe(false);
    expect(store.lastRun).toBeUndefined();
  });
});
