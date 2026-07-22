import type { AssetsWithId } from '@/modules/assets/types';
import type { SearchMatcher, Suggestion } from '@/modules/core/table/filtering';
import { describe, expect, it } from 'vitest';
import { useFilterModel } from '@/modules/core/table/use-filter-model';

const matchers: SearchMatcher<string, string>[] = [
  {
    description: 'Type',
    key: 'type',
    keyValue: 'types',
    multiple: true,
    string: true,
    suggestions: (): string[] => [],
    validate: (): boolean => true,
  },
  {
    description: 'Protocol',
    key: 'protocol',
    keyValue: 'protocols',
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

describe('useFilterModel', () => {
  it('should derive matches from the selection', () => {
    const model = useFilterModel(byKey, byKeyValue);
    model.setSelection([chip('type', 'a'), chip('type', 'b')]);
    expect(get(model.matches)).toEqual({ types: ['a', 'b'] });
  });

  it('should drop chips that fail validation on setSelection', () => {
    const model = useFilterModel(byKey, byKeyValue);
    model.setSelection([chip('amount', '100'), chip('amount', 'abc')]);
    expect(get(model.selection)).toHaveLength(1);
    expect(get(model.matches)).toEqual({ amount: '100' });
  });

  it('should clear all chips', () => {
    const model = useFilterModel(byKey, byKeyValue);
    model.setSelection([chip('type', 'a')]);
    model.clearAll();
    expect(get(model.selection)).toEqual([]);
    expect(get(model.matches)).toEqual({});
  });

  it('should rebuild the selection from a genuinely external matches', () => {
    const model = useFilterModel(byKey, byKeyValue);
    model.setFromMatches({ protocols: ['uniswap'], types: ['a'] });
    expect(get(model.matches)).toEqual({ protocols: ['uniswap'], types: ['a'] });
    expect(get(model.selection).map(chip => chip.key)).toContain('type');
    expect(get(model.selection).map(chip => chip.key)).toContain('protocol');
  });

  describe('self-echo (PR #12584)', () => {
    it('should NOT regroup or reorder chips when its own matches echoes back', () => {
      const model = useFilterModel(byKey, byKeyValue);
      // Interleaved order that grouping would rearrange: type, protocol, type.
      const interleaved = [chip('type', 'a'), chip('protocol', 'x'), chip('type', 'b')];
      model.setSelection(interleaved);

      // The echo of the derived matches (as the table would round-trip it back).
      model.setFromMatches(get(model.matches));

      // Order preserved — not collapsed to [type a, type b, protocol x].
      expect(get(model.selection).map(item => [item.key, item.value])).toEqual([
        ['type', 'a'],
        ['protocol', 'x'],
        ['type', 'b'],
      ]);
    });

    it('should skip rebuilding when the source is self', () => {
      const model = useFilterModel(byKey, byKeyValue);
      model.setSelection([chip('type', 'a')]);
      // A different matches, but tagged self: must be ignored.
      model.setFromMatches({ types: ['z'] }, 'self');
      expect(get(model.selection)).toEqual([expect.objectContaining({ key: 'type', value: 'a' })]);
    });
  });
});
