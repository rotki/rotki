import type { AssetsWithId } from '@/modules/assets/types';
import type { SearchMatcher } from '@/modules/core/table/filtering';
import { describe, expect, it } from 'vitest';
import { resolveEditor, resolveValueType, toDateFieldDef, toFieldDef, toParamFieldDef, toRangeFieldDef } from '@/modules/core/table/pill/core/field-adapter';

const stringMatcher: SearchMatcher<string, string> = {
  allowExclusion: true,
  description: 'Protocol',
  key: 'protocol',
  keyValue: 'protocols',
  multiple: true,
  serializer: (v: string): string => v.toLowerCase(),
  string: true,
  suggestions: (): string[] => ['aave', 'uniswap'],
  validate: (): boolean => true,
};

const assetMatcher: SearchMatcher<string, string> = {
  asset: true,
  description: 'Asset',
  key: 'asset',
  keyValue: 'assets',
  suggestions: async (): Promise<AssetsWithId> => [],
};

const booleanMatcher: SearchMatcher<string, string> = {
  boolean: true,
  description: 'Ignored',
  key: 'ignored',
  keyValue: 'ignored',
};

describe('field-adapter', () => {
  describe('resolveValueType', () => {
    it('should honor an explicit valueType override', () => {
      expect(resolveValueType({ ...stringMatcher, valueType: 'range' })).toBe('range');
    });

    it('should map the discriminant when no override is set', () => {
      expect(resolveValueType(stringMatcher)).toBe('enum');
      expect(resolveValueType(assetMatcher)).toBe('asset');
      expect(resolveValueType(booleanMatcher)).toBe('boolean');
    });
  });

  describe('toFieldDef', () => {
    it('should normalize a string matcher into an enum field bound to matches', () => {
      const f = toFieldDef(stringMatcher);
      expect(f.key).toBe('protocols');
      expect(f.valueType).toBe('enum');
      expect(f.multiple).toBe(true);
      expect(f.allowExclusion).toBe(true);
      expect(f.binding).toStrictEqual({ kind: 'matcher' });
      expect(f.operators).toStrictEqual(['is', 'is_not']);
      expect(f.suggest?.()).toStrictEqual(['aave', 'uniswap']);
      expect(f.serializer?.('AAVE')).toBe('aave');
      expect(f.searchAsset).toBeUndefined();
    });

    it('should normalize an asset matcher with async search and no exclusion', () => {
      const f = toFieldDef(assetMatcher);
      expect(f.valueType).toBe('asset');
      expect(f.allowExclusion).toBe(false);
      expect(f.operators).toStrictEqual(['is']);
      expect(f.searchAsset).toBe(assetMatcher.suggestions);
      expect(f.suggest).toBeUndefined();
    });

    it('should give a boolean matcher a single is operator', () => {
      const f = toFieldDef(booleanMatcher);
      expect(f.valueType).toBe('boolean');
      expect(f.operators).toStrictEqual(['is']);
    });

    it('should offer is_not only when the string matcher allows exclusion', () => {
      expect(toFieldDef(stringMatcher).operators).toStrictEqual(['is', 'is_not']);
      expect(toFieldDef({ ...stringMatcher, allowExclusion: false }).operators).toStrictEqual(['is']);
    });

    it('should carry an explicit valueType and operators through', () => {
      const f = toFieldDef({ ...stringMatcher, operators: ['gt', 'lt'], valueType: 'range' });
      expect(f.valueType).toBe('range');
      expect(f.operators).toStrictEqual(['gt', 'lt']);
    });
  });

  describe('toParamFieldDef', () => {
    it('should model an external param filter as a param-bound field', () => {
      const f = toParamFieldDef({
        key: 'accounts',
        label: 'Accounts',
        paramKey: 'locationLabels',
        to: 'both',
        valueType: 'asset',
      });
      expect(f.binding).toStrictEqual({ kind: 'param', paramKey: 'locationLabels', to: 'both' });
      expect(f.valueType).toBe('asset');
      expect(f.multiple).toBe(true);
      expect(f.operators).toStrictEqual(['is']);
    });

    it('should default to a multi enum field', () => {
      const f = toParamFieldDef({ key: 'x', label: 'X', paramKey: 'x', to: 'request' });
      expect(f.valueType).toBe('enum');
      expect(f.multiple).toBe(true);
    });

    // A param sends a plain list, so there is no place to put the `!` the codec writes for an
    // excluding matcher. Offering `is not` would render a chip that silently drops the filter.
    it('should not offer exclusion it cannot serialize', () => {
      const f = toParamFieldDef({ key: 'x', label: 'X', paramKey: 'x', to: 'request' });
      expect(f.allowExclusion).toBe(false);
      expect(f.operators).toStrictEqual(['is']);
    });

    it('should keep the range operators, which are expressed by the bound sent', () => {
      const f = toParamFieldDef({ key: 'x', label: 'X', paramKey: 'x', to: 'request', valueType: 'range' });
      expect(f.operators).toStrictEqual(['between', 'gt', 'lt']);
    });

    it('should honour explicit operators over the derived ones', () => {
      const f = toParamFieldDef({ key: 'x', label: 'X', operators: ['is', 'is_not'], paramKey: 'x', to: 'request' });
      expect(f.operators).toStrictEqual(['is', 'is_not']);
    });
  });

  describe('toRangeFieldDef', () => {
    it('should collapse two amount bounds into a matcher-bound range field', () => {
      const f = toRangeFieldDef({ key: 'amount', label: 'Amount', lowerKey: 'minAmount', upperKey: 'maxAmount' });
      expect(f.valueType).toBe('range');
      expect(f.binding).toStrictEqual({ kind: 'matcher' });
      expect(f.bounds).toStrictEqual({ lower: 'minAmount', upper: 'maxAmount' });
      expect(f.multiple).toBe(false);
      expect(f.allowExclusion).toBe(false);
      expect(f.operators).toStrictEqual(['between', 'gt', 'lt']);
      expect(resolveEditor(f)).toBe('range');
    });
  });

  describe('toDateFieldDef', () => {
    it('should collapse two period bounds into a date field carrying the bound serializers', () => {
      const f = toDateFieldDef({
        deserializer: (v: string): string => `d:${v}`,
        key: 'period',
        label: 'Period',
        lowerKey: 'fromTimestamp',
        serializer: (v: string): string => `ts:${v}`,
        upperKey: 'toTimestamp',
      });
      expect(f.valueType).toBe('date');
      expect(f.bounds).toStrictEqual({ lower: 'fromTimestamp', upper: 'toTimestamp' });
      expect(f.operators).toStrictEqual(['between', 'after', 'before']);
      expect(f.serializer?.('2024-01-01')).toBe('ts:2024-01-01');
      expect(f.deserializer?.('1700000000')).toBe('d:1700000000');
      expect(resolveEditor(f)).toBe('date');
    });
  });

  describe('resolveEditor', () => {
    it('should map value types to their editors', () => {
      expect(resolveEditor(toFieldDef(stringMatcher))).toBe('enum');
      expect(resolveEditor(toFieldDef(assetMatcher))).toBe('asset');
      expect(resolveEditor(toFieldDef(booleanMatcher))).toBe('boolean');
      expect(resolveEditor(toFieldDef({ ...stringMatcher, valueType: 'range' }))).toBe('range');
      expect(resolveEditor(toFieldDef({ ...stringMatcher, valueType: 'date' }))).toBe('date');
    });
  });
});
