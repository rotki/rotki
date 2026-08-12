import type { ActiveFilter, FieldDef } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { pillOperator, pillStateSummary, pillValueSummary } from '@/modules/core/table/pill/core/format';

// The core works in operators; the words come from the Vue layer, which is what makes them
// translatable. These stand in for it.
const operatorLabels = {
  after: 'after',
  before: 'before',
  between: 'between',
  gt: 'greater than',
  is: 'is',
  is_not: 'is not',
  lt: 'less than',
} as const;

function field(partial: Partial<FieldDef>): FieldDef {
  return {
    allowExclusion: true,
    binding: { kind: 'filter' },
    key: 'k',
    label: 'K',
    multiple: true,
    operators: ['is', 'is_not'],
    valueType: 'enum',
    ...partial,
  };
}

function filter(partial: Partial<ActiveFilter>): ActiveFilter {
  return { fieldKey: 'k', op: 'is', values: [], ...partial };
}

describe('pill format', () => {
  describe('pillOperator', () => {
    it('should hide the default operator', () => {
      expect(pillOperator(field({}), filter({ op: 'is' }))).toBeUndefined();
    });

    // The op itself, not a word: the words are the Vue layer's, which is what makes them
    // translatable at all.
    it('should name a non-default operator', () => {
      expect(pillOperator(field({}), filter({ op: 'is_not' }))).toBe('is_not');
    });
  });

  describe('pillValueSummary', () => {
    it('should render nothing for a boolean field', () => {
      expect(pillValueSummary(field({ valueType: 'boolean' }), filter({}))).toBe('');
    });

    it('should list up to two enum values, then summarize the overflow', () => {
      expect(pillValueSummary(field({}), filter({ values: ['a'] }))).toBe('a');
      expect(pillValueSummary(field({}), filter({ values: ['a', 'b'] }))).toBe('a, b');
      expect(pillValueSummary(field({}), filter({ values: ['a', 'b', 'c'] }))).toBe('a +2');
    });

    it('should summarize a range with open ends', () => {
      expect(pillValueSummary(field({ valueType: 'range' }), filter({ range: { min: '1', max: '9' } }))).toBe('1 - 9');
      expect(pillValueSummary(field({ valueType: 'range' }), filter({ range: { min: '1' } }))).toBe('≥ 1');
      expect(pillValueSummary(field({ valueType: 'range' }), filter({}))).toBe('');
    });

    it('should read a half-filled range as the bound it has', () => {
      expect(pillValueSummary(field({ valueType: 'range' }), filter({ range: { min: '10' } }))).toBe('≥ 10');
      expect(pillValueSummary(field({ valueType: 'range' }), filter({ range: { max: '50' } }))).toBe('≤ 50');
    });

    it('should prefer a date preset, else the from/to span', () => {
      expect(pillValueSummary(field({ valueType: 'date' }), filter({ date: { preset: 'last 7 days' } }))).toBe('last 7 days');
      expect(pillValueSummary(field({ valueType: 'date' }), filter({ date: { from: '2024' } }))).toBe('≥ 2024');
      expect(pillValueSummary(field({ valueType: 'date' }), filter({}))).toBe('');
    });
  });

  describe('pillStateSummary', () => {
    const location = field({ key: 'location', label: 'Location', multiple: false });
    const account = field({
      binding: { kind: 'param', paramKey: 'locationLabels', to: 'both' },
      key: 'account',
      label: 'Account',
    });
    const ignored = field({ key: 'showIgnored', label: 'Ignored', valueType: 'boolean' });

    it('should name every field a stored set holds, from both halves', () => {
      const summary = pillStateSummary(
        { location: 'kraken' },
        { locationLabels: ['0xaaa', '0xbbb'] },
        [location, account],
        operatorLabels,
      );

      expect(summary).toBe('Location: kraken · Account: 0xaaa, 0xbbb');
    });

    it('should show a non-default operator and a bare label for a boolean', () => {
      const summary = pillStateSummary({ location: '!kraken', showIgnored: true }, {}, [location, ignored], operatorLabels);

      expect(summary).toBe('Location is not: kraken · Ignored');
    });

    // A view saved before a field was removed from the table still reads as what is left of it,
    // rather than as a broken row.
    it('should drop what the given fields cannot describe', () => {
      expect(pillStateSummary({ gone: 'x', location: 'kraken' }, {}, [location], operatorLabels)).toBe('Location: kraken');
      expect(pillStateSummary({}, {}, [location], operatorLabels)).toBe('');
    });
  });
});
