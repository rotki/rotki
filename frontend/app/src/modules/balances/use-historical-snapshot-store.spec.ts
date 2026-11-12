import { bigNumberify } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useHistoricalSnapshotStore } from './use-historical-snapshot-store';

describe('useHistoricalSnapshotStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should report nothing loaded until a snapshot is set', () => {
    const store = useHistoricalSnapshotStore();

    expect(store.loaded).toBe(false);
    expect(store.entries).toStrictEqual([]);
  });

  it('should keep the entries and flags of the snapshot it is given', () => {
    const store = useHistoricalSnapshotStore();
    const entries = [{ amount: bigNumberify(2), asset: 'ETH', location: 'ethereum', locationLabel: '0xA', protocol: null }];

    store.setSnapshot({ entries, processingRequired: true, stale: true });

    expect(store.loaded).toBe(true);
    expect(store.entries).toStrictEqual(entries);
    expect(store.processingRequired).toBe(true);
    expect(store.stale).toBe(true);
  });
});
