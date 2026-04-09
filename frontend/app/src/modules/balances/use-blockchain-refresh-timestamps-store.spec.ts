import { beforeEach, describe, expect, it } from 'vitest';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';

describe('useBlockchainRefreshTimestampsStore', () => {
  let store: ReturnType<typeof useBlockchainRefreshTimestampsStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useBlockchainRefreshTimestampsStore();
  });

  it('should start with empty timestamps', () => {
    expect(get(store.refreshTimestamps)).toEqual({});
  });

  it('should update timestamps', () => {
    store.updateTimestamps({ eth: 1000, btc: 2000 });
    expect(get(store.refreshTimestamps)).toEqual({ eth: 1000, btc: 2000 });
  });

  it('should merge new timestamps with existing ones', () => {
    store.updateTimestamps({ eth: 1000 });
    store.updateTimestamps({ btc: 2000 });
    expect(get(store.refreshTimestamps)).toEqual({ eth: 1000, btc: 2000 });
  });

  it('should overwrite existing chain timestamps', () => {
    store.updateTimestamps({ eth: 1000 });
    store.updateTimestamps({ eth: 3000 });
    expect(get(store.refreshTimestamps)).toEqual({ eth: 3000 });
  });

  it('should return timestamp for a specific chain via getTimestamp', () => {
    store.updateTimestamps({ eth: 1000, btc: 2000 });
    const ethTimestamp = store.getTimestamp('eth');
    const btcTimestamp = store.getTimestamp('btc');
    expect(get(ethTimestamp)).toBe(1000);
    expect(get(btcTimestamp)).toBe(2000);
  });

  it('should return undefined for unknown chain via getTimestamp', () => {
    const timestamp = store.getTimestamp('unknown');
    expect(get(timestamp)).toBeUndefined();
  });

  it('should reset all timestamps', () => {
    store.updateTimestamps({ eth: 1000, btc: 2000 });
    store.reset();
    expect(get(store.refreshTimestamps)).toEqual({});
  });
});
