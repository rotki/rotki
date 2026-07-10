import type { KrakenStakingEvents } from '@/modules/staking/staking-types';
import { bigNumberify, Zero } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';

const mockResolve = vi.fn((asset: string) => asset);

vi.mock('@/modules/assets/use-resolve-asset-identifier', () => ({
  useResolveAssetIdentifier: (): typeof mockResolve => mockResolve,
}));

function events(received: KrakenStakingEvents['received']): KrakenStakingEvents {
  return {
    assets: [],
    entriesFound: received.length,
    entriesLimit: 0,
    entriesTotal: received.length,
    received,
    totalValue: Zero,
  };
}

describe('useKrakenStakingStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockResolve.mockImplementation((asset: string) => asset);
  });

  it('should start with default pagination and empty events', () => {
    const store = useKrakenStakingStore();
    expect(get(store.pagination)).toEqual({
      ascending: [false],
      limit: 10,
      offset: 0,
      orderByAttributes: ['timestamp'],
    });
    expect(get(store.events).received).toEqual([]);
    expect(get(store.events).assets).toEqual([]);
  });

  it('should resolve asset identifiers and list them under assets', () => {
    const store = useKrakenStakingStore();
    store.rawEvents = events([
      { amount: bigNumberify(1), asset: 'ETH', value: bigNumberify(100) },
    ]);
    expect(get(store.events).assets).toEqual(['ETH']);
  });

  it('should aggregate received entries that resolve to the same asset', () => {
    mockResolve.mockImplementation(() => 'ETH');
    const store = useKrakenStakingStore();
    store.rawEvents = events([
      { amount: bigNumberify(1), asset: 'ETH', value: bigNumberify(100) },
      { amount: bigNumberify(2), asset: 'ETH2', value: bigNumberify(200) },
    ]);

    const result = get(store.events);
    expect(result.assets).toEqual(['ETH']);
    expect(result.received).toHaveLength(1);
    expect(result.received[0].amount.toNumber()).toBe(3);
    expect(result.received[0].value.toNumber()).toBe(300);
  });

  it('should keep entries that resolve to different assets separate', () => {
    const store = useKrakenStakingStore();
    store.rawEvents = events([
      { amount: bigNumberify(1), asset: 'ETH', value: bigNumberify(100) },
      { amount: bigNumberify(2), asset: 'BTC', value: bigNumberify(200) },
    ]);

    const result = get(store.events);
    expect(result.assets).toEqual(['ETH', 'BTC']);
    expect(result.received).toHaveLength(2);
  });
});
