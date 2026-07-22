import type { AssetInfoWithId } from '@rotki/common';
import type { AssetsWithId } from '@/modules/assets/types';
import type { SearchMatcher, Suggestion } from '@/modules/core/table/filtering';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { matchesFromSelection, selectionFromMatches } from '@/modules/core/table/filter-codec';

const matchers: SearchMatcher<string, string>[] = [
  {
    allowExclusion: true,
    description: 'Type',
    key: 'type',
    keyValue: 'types',
    multiple: true,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
  {
    description: 'Amount',
    key: 'amount',
    keyValue: 'amount',
    string: true,
    suggestions: (): string[] => [],
    validate: (value: string): boolean => /^\d+$/.test(value),
  },
  {
    asset: true,
    description: 'Asset',
    key: 'asset',
    keyValue: 'assets',
    suggestions: async (): Promise<AssetsWithId> => [],
  },
  {
    boolean: true,
    description: 'Ignored',
    key: 'ignored',
    keyValue: 'ignored',
  },
];

function byKey(key: string | undefined): SearchMatcher<string, string> | undefined {
  return matchers.find(matcher => matcher.key === key);
}

function byKeyValue(key: string | undefined): SearchMatcher<string, string> | undefined {
  return matchers.find(matcher => matcher.keyValue === key);
}

function chip(key: string, value: Suggestion['value'], exclude = false): Suggestion {
  return { asset: false, exclude, index: 0, key, total: 1, value };
}

describe('filter codec', () => {
  describe('matchesFromSelection', () => {
    it('should group a multiple matcher into an array and encode exclusion with "!"', () => {
      const { matches } = matchesFromSelection([chip('type', 'a'), chip('type', 'b', true)], byKey);
      expect(matches).toEqual({ types: ['a', '!b'] });
    });

    it('should drop a value that fails the matcher validate', () => {
      const { matches, validSelection } = matchesFromSelection(
        [chip('amount', '100'), chip('amount', 'abc')],
        byKey,
      );
      expect(matches).toEqual({ amount: '100' });
      expect(validSelection).toHaveLength(1);
      expect(validSelection[0].value).toBe('100');
    });

    it('should serialize an asset chip to its identifier', () => {
      const asset = createMock<AssetInfoWithId>({ identifier: 'ETH', symbol: 'ETH' });
      const { matches } = matchesFromSelection([{ ...chip('asset', asset), asset: true }], byKey);
      expect(matches).toEqual({ assets: 'ETH' });
    });

    it('should encode a boolean matcher as true', () => {
      const { matches } = matchesFromSelection([chip('ignored', true)], byKey);
      expect(matches).toEqual({ ignored: true });
    });

    it('should skip a chip whose key has no matcher', () => {
      const { matches, validSelection } = matchesFromSelection([chip('unknown', 'x')], byKey);
      expect(matches).toEqual({});
      expect(validSelection).toEqual([]);
    });
  });

  describe('selectionFromMatches', () => {
    it('should rebuild chips and decode "!" as exclusion', () => {
      const selection = selectionFromMatches({ types: ['a', '!b'] }, byKeyValue);
      expect(selection).toHaveLength(2);
      expect(selection[0]).toMatchObject({ exclude: false, key: 'type', value: 'a' });
      expect(selection[1]).toMatchObject({ exclude: true, key: 'type', value: 'b' });
    });

    it('should rebuild a boolean chip', () => {
      const selection = selectionFromMatches({ ignored: true }, byKeyValue);
      expect(selection).toEqual([expect.objectContaining({ key: 'ignored', value: true })]);
    });

    it('should preserve a resolved asset value from the previous selection', () => {
      const asset = createMock<AssetInfoWithId>({ identifier: 'ETH', symbol: 'ETH' });
      const previous: Suggestion[] = [{ ...chip('asset', asset), asset: true }];
      const selection = selectionFromMatches({ assets: 'ETH' }, byKeyValue, previous);
      expect(selection[0].value).toBe(asset);
    });

    it('should skip a key with no matcher', () => {
      expect(selectionFromMatches({ unknown: 'x' }, byKeyValue)).toEqual([]);
    });
  });

  describe('round-trip', () => {
    it('should be stable across selection -> matches -> selection for the common types', () => {
      const start: Suggestion[] = [chip('type', 'a'), chip('type', 'b', true), chip('ignored', true)];
      const { matches, validSelection } = matchesFromSelection(start, byKey);
      const back = selectionFromMatches(matches, byKeyValue);

      // Same keys/values/exclusion survive the round-trip (the property #12584 needed).
      expect(back.map(item => ({ exclude: item.exclude, key: item.key, value: item.value })))
        .toEqual(validSelection.map(item => ({ exclude: item.exclude, key: item.key, value: item.value })));
    });
  });
});
