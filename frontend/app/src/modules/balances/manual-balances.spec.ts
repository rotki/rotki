import type { ManualBalanceRequestPayload, ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { sortAndFilterManualBalance } from './manual-balances';

let nextId = 1;

function balance(overrides: Partial<ManualBalanceWithValue> = {}): ManualBalanceWithValue {
  return {
    amount: bigNumberify(1),
    asset: 'ETH',
    balanceType: BalanceType.ASSET,
    identifier: nextId++,
    label: 'a label',
    location: 'external',
    tags: null,
    value: bigNumberify(1),
    ...overrides,
  };
}

function payload(overrides: Partial<ManualBalanceRequestPayload> = {}): ManualBalanceRequestPayload {
  return { limit: 10, offset: 0, ...overrides };
}

function pricesOf(prices: Record<string, number>): { resolveAssetPrice: (asset: string) => BigNumber | undefined } {
  return {
    resolveAssetPrice: (asset: string) => asset in prices ? bigNumberify(prices[asset]) : undefined,
  };
}

const noPrices = pricesOf({});

describe('modules/balances/sortAndFilterManualBalance', () => {
  describe('the collection it returns', () => {
    it('should report the unfiltered count as the total and the filtered count as found', () => {
      const balances = [balance({ label: 'keep' }), balance({ label: 'drop' }), balance({ label: 'drop' })];

      const result = sortAndFilterManualBalance(balances, payload({ label: 'keep' }), noPrices);

      expect(result.found).toBe(1);
      expect(result.total).toBe(3);
    });

    it('should always report a limit of -1, since it paginates in memory', () => {
      const result = sortAndFilterManualBalance([balance()], payload(), noPrices);

      expect(result.limit).toBe(-1);
    });

    it('should attach the price to each row', () => {
      const balances = [balance({ asset: 'ETH' }), balance({ asset: 'UNKNOWN' })];

      const result = sortAndFilterManualBalance(balances, payload(), pricesOf({ ETH: 3000 }));

      expect(result.data[0].price?.toNumber()).toBe(3000);
      expect(result.data[1].price).toBeUndefined();
    });
  });

  describe('pagination', () => {
    it('should return the requested page', () => {
      const balances = [balance({ label: 'a' }), balance({ label: 'b' }), balance({ label: 'c' })];

      const result = sortAndFilterManualBalance(balances, payload({ limit: 2, offset: 1 }), noPrices);

      expect(result.data.map(item => item.label)).toEqual(['b', 'c']);
    });

    it('should report the full count even when a page is returned', () => {
      const balances = [balance(), balance(), balance()];

      const result = sortAndFilterManualBalance(balances, payload({ limit: 1, offset: 0 }), noPrices);

      expect(result.data).toHaveLength(1);
      expect(result.found).toBe(3);
    });
  });

  describe('the total value', () => {
    it('should sum price times amount over every filtered row, not just the page', () => {
      const balances = [
        balance({ amount: bigNumberify(2), asset: 'ETH' }),
        balance({ amount: bigNumberify(3), asset: 'ETH' }),
      ];

      const result = sortAndFilterManualBalance(balances, payload({ limit: 1 }), pricesOf({ ETH: 100 }));

      expect(result.data).toHaveLength(1);
      expect(result.totalValue?.toNumber()).toBe(500);
    });

    it('should skip an unpriced asset rather than counting its amount', () => {
      const balances = [
        balance({ amount: bigNumberify(2), asset: 'ETH' }),
        balance({ amount: bigNumberify(99), asset: 'UNKNOWN' }),
      ];

      const result = sortAndFilterManualBalance(balances, payload(), pricesOf({ ETH: 100 }));

      expect(result.totalValue?.toNumber()).toBe(200);
    });

    it('should skip an asset priced at zero', () => {
      const balances = [balance({ amount: bigNumberify(2), asset: 'ETH' })];

      const result = sortAndFilterManualBalance(balances, payload(), pricesOf({ ETH: 0 }));

      expect(result.totalValue?.toNumber()).toBe(0);
    });

    it('should count only what survives the filter', () => {
      const balances = [
        balance({ amount: bigNumberify(2), asset: 'ETH', label: 'keep' }),
        balance({ amount: bigNumberify(5), asset: 'ETH', label: 'drop' }),
      ];

      const result = sortAndFilterManualBalance(balances, payload({ label: 'keep' }), pricesOf({ ETH: 100 }));

      expect(result.totalValue?.toNumber()).toBe(200);
    });
  });

  describe('filtering', () => {
    it('should return everything when no filter is given', () => {
      const balances = [balance(), balance()];

      expect(sortAndFilterManualBalance(balances, payload(), noPrices).found).toBe(2);
    });

    it('should treat an empty tag list as no filter at all', () => {
      const balances = [balance({ tags: null }), balance({ tags: ['x'] })];

      expect(sortAndFilterManualBalance(balances, payload({ tags: [] }), noPrices).found).toBe(2);
    });

    it('should match a label partially', () => {
      const balances = [balance({ label: 'my savings' }), balance({ label: 'other' })];

      const result = sortAndFilterManualBalance(balances, payload({ label: 'saving' }), noPrices);

      expect(result.data.map(item => item.label)).toEqual(['my savings']);
    });

    it('should match a location partially', () => {
      const balances = [balance({ location: 'kraken' }), balance({ location: 'external' })];

      const result = sortAndFilterManualBalance(balances, payload({ location: 'krak' }), noPrices);

      expect(result.data.map(item => item.location)).toEqual(['kraken']);
    });

    it('should match an asset exactly, not partially', () => {
      const balances = [balance({ asset: 'ETH' }), balance({ asset: 'ETHW' })];

      const result = sortAndFilterManualBalance(balances, payload({ asset: 'ETH' }), noPrices);

      expect(result.data.map(item => item.asset)).toEqual(['ETH']);
    });

    it('should ignore surrounding whitespace when matching an asset', () => {
      const balances = [balance({ asset: ' ETH ' })];

      expect(sortAndFilterManualBalance(balances, payload({ asset: 'ETH' }), noPrices).found).toBe(1);
    });

    it('should keep a row carrying any one of the requested tags', () => {
      const balances = [balance({ tags: ['b'] }), balance({ tags: ['c'] })];

      const result = sortAndFilterManualBalance(balances, payload({ tags: ['a', 'b'] }), noPrices);

      expect(result.data.map(item => item.tags)).toEqual([['b']]);
    });

    it('should drop a row with no tags when a tag is required', () => {
      const balances = [balance({ tags: null })];

      expect(sortAndFilterManualBalance(balances, payload({ tags: ['a'] }), noPrices).found).toBe(0);
    });

    it('should require every given filter to match, not any', () => {
      const balances = [
        balance({ asset: 'ETH', label: 'keep' }),
        balance({ asset: 'BTC', label: 'keep' }),
      ];

      const result = sortAndFilterManualBalance(balances, payload({ asset: 'ETH', label: 'keep' }), noPrices);

      expect(result.found).toBe(1);
    });
  });

  describe('sorting', () => {
    it('should leave the order alone when no attribute is given', () => {
      const balances = [balance({ label: 'b' }), balance({ label: 'a' })];

      const result = sortAndFilterManualBalance(balances, payload(), noPrices);

      expect(result.data.map(item => item.label)).toEqual(['b', 'a']);
    });

    it('should sort a text column ascending', () => {
      const balances = [balance({ label: 'b' }), balance({ label: 'a' })];

      const result = sortAndFilterManualBalance(
        balances,
        payload({ ascending: [true], orderByAttributes: ['label'] }),
        noPrices,
      );

      expect(result.data.map(item => item.label)).toEqual(['a', 'b']);
    });

    it('should sort a text column descending', () => {
      const balances = [balance({ label: 'a' }), balance({ label: 'b' })];

      const result = sortAndFilterManualBalance(
        balances,
        payload({ ascending: [false], orderByAttributes: ['label'] }),
        noPrices,
      );

      expect(result.data.map(item => item.label)).toEqual(['b', 'a']);
    });

    it('should sort a numeric column by magnitude rather than as text', () => {
      const balances = [
        balance({ amount: bigNumberify(9), label: 'nine' }),
        balance({ amount: bigNumberify(10), label: 'ten' }),
      ];

      const result = sortAndFilterManualBalance(
        balances,
        payload({ ascending: [true], orderByAttributes: ['amount'] }),
        noPrices,
      );

      expect(result.data.map(item => item.label)).toEqual(['nine', 'ten']);
    });

    it('should accept the snake_case attribute getApiSortingParams produces, not the camelCase key', () => {
      const balances = [
        balance({ balanceType: BalanceType.LIABILITY, label: 'liability' }),
        balance({ balanceType: BalanceType.ASSET, label: 'asset' }),
      ];

      const result = sortAndFilterManualBalance(
        balances,
        payload({ ascending: [true], orderByAttributes: ['balance_type'] }),
        noPrices,
      );

      expect(result.data.map(item => item.label)).toEqual(['asset', 'liability']);
    });

    it('should ignore an optional attribute that is absent from the rows', () => {
      const balances = [balance({ label: 'b' }), balance({ label: 'a' })];

      const result = sortAndFilterManualBalance(
        balances,
        payload({ ascending: [true], orderByAttributes: ['asset_is_missing'] }),
        noPrices,
      );

      expect(result.data.map(item => item.label)).toEqual(['b', 'a']);
    });

    it('should fall through to the second attribute when the first ties', () => {
      const balances = [
        balance({ label: 'b', location: 'same' }),
        balance({ label: 'a', location: 'same' }),
      ];

      const result = sortAndFilterManualBalance(
        balances,
        payload({ ascending: [true, true], orderByAttributes: ['location', 'label'] }),
        noPrices,
      );

      expect(result.data.map(item => item.label)).toEqual(['a', 'b']);
    });

    it('should not reorder the caller\'s array when no filter narrows it first', () => {
      const balances = [balance({ label: 'b' }), balance({ label: 'a' })];

      sortAndFilterManualBalance(balances, payload({ ascending: [true], orderByAttributes: ['label'] }), noPrices);

      expect(balances.map(item => item.label)).toEqual(['b', 'a']);
    });
  });
});
