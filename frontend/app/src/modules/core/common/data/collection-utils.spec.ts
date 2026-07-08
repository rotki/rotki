import type { Collection, CollectionResponse } from '@/modules/core/common/collection';
import { bigNumberify, Zero } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  defaultCollectionState,
  getCollectionData,
  mapCollectionResponse,
  setupEntryLimit,
} from './collection-utils';

const premium = ref<boolean>(false);

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): typeof premium => premium,
}));

describe('mapCollectionResponse', () => {
  it('should rename entry fields and keep the rest', () => {
    const response: CollectionResponse<number> & { extra: string } = {
      entries: [1, 2],
      entriesFound: 2,
      entriesLimit: 10,
      entriesTotal: 5,
      extra: 'keep',
    };
    expect(mapCollectionResponse(response)).toEqual({
      data: [1, 2],
      found: 2,
      limit: 10,
      total: 5,
      extra: 'keep',
    });
  });
});

describe('defaultCollectionState', () => {
  it('should return an empty collection with a zero total value', () => {
    const state = defaultCollectionState<string>();
    expect(state).toEqual({ data: [], found: 0, limit: 0, total: 0, totalValue: Zero });
  });
});

describe('getCollectionData', () => {
  it('should expose each collection field as a computed', () => {
    const collection: Collection<number> = {
      data: [1, 2, 3],
      limit: 10,
      found: 3,
      total: 8,
      entriesFoundTotal: 12,
      totalValue: bigNumberify(100),
    };
    const { data, entriesFoundTotal, found, limit, total, totalValue } = getCollectionData(collection);
    expect(get(data)).toEqual([1, 2, 3]);
    expect(get(limit)).toBe(10);
    expect(get(found)).toBe(3);
    expect(get(total)).toBe(8);
    expect(get(entriesFoundTotal)).toBe(12);
    expect(get(totalValue)).toEqual(bigNumberify(100));
  });

  it('should react to a source ref changing', () => {
    const source = ref<Collection<number>>(defaultCollectionState<number>());
    const { found } = getCollectionData(source);
    expect(get(found)).toBe(0);
    set(source, { ...defaultCollectionState<number>(), found: 4 });
    expect(get(found)).toBe(4);
  });
});

describe('setupEntryLimit', () => {
  beforeEach(() => {
    set(premium, false);
  });

  it('should cap the item length at the limit for non-premium users', () => {
    const { itemLength } = setupEntryLimit(ref(10), ref(50), ref(50));
    expect(get(itemLength)).toBe(10);
  });

  it('should return the full found count for premium users', () => {
    set(premium, true);
    const { itemLength } = setupEntryLimit(ref(10), ref(50), ref(50));
    expect(get(itemLength)).toBe(50);
  });

  it('should treat a -1 limit as unlimited', () => {
    const { itemLength } = setupEntryLimit(ref(-1), ref(50), ref(50));
    expect(get(itemLength)).toBe(50);
  });

  it('should show the upgrade row when the limit is reached', () => {
    const { showUpgradeRow } = setupEntryLimit(ref(10), ref(50), ref(50));
    expect(get(showUpgradeRow)).toBe(true);
  });

  it('should hide the upgrade row when the limit exceeds the total', () => {
    const { showUpgradeRow } = setupEntryLimit(ref(100), ref(50), ref(50));
    expect(get(showUpgradeRow)).toBe(false);
  });

  it('should compare found against entryFoundTotal when provided', () => {
    const { showUpgradeRow } = setupEntryLimit(ref(10), ref(5), ref(50), ref(8));
    expect(get(showUpgradeRow)).toBe(true);
  });

  it('should hide the upgrade row when found matches entryFoundTotal', () => {
    const { showUpgradeRow } = setupEntryLimit(ref(10), ref(8), ref(50), ref(8));
    expect(get(showUpgradeRow)).toBe(false);
  });
});
