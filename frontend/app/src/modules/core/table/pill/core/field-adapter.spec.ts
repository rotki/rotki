import type { AssetsWithId } from '@/modules/assets/types';
import type { FilterValueType } from '@/modules/core/table/filtering';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { resolveEditor, toDateFieldDef, toMatchFieldDef, toParamFieldDef, toRangeFieldDef } from '@/modules/core/table/pill/core/field-adapter';

describe('field-adapter', () => {
  describe('toMatchFieldDef', () => {
    it('should declare a field bound to the table filter bag', () => {
      const f = toMatchFieldDef({
        allowExclusion: true,
        key: 'protocols',
        label: 'Protocol',
        multiple: true,
        suggest: (): string[] => ['aave'],
      });

      expect(f.binding).toStrictEqual({ kind: 'filter' });
      expect(f.valueType).toBe('enum');
      expect(f.multiple).toBe(true);
      expect(f.suggest?.()).toStrictEqual(['aave']);
    });

    it('should default to a single enum field', () => {
      const f = toMatchFieldDef({ key: 'x', label: 'X' });

      expect(f.valueType).toBe('enum');
      expect(f.multiple).toBe(false);
      expect(f.allowExclusion).toBe(false);
    });

    it('should carry an explicit valueType and operators through', () => {
      const f = toMatchFieldDef({ key: 'amount', label: 'Amount', operators: ['gt', 'lt'], valueType: 'range' });

      expect(f.valueType).toBe('range');
      expect(f.operators).toStrictEqual(['gt', 'lt']);
    });

    it('should carry an async asset search rather than an option list', () => {
      const searchAsset = async (): Promise<AssetsWithId> => [];
      const f = toMatchFieldDef({ key: 'asset', label: 'Asset', searchAsset, valueType: 'asset' });

      expect(f.searchAsset).toBe(searchAsset);
      expect(f.suggest).toBeUndefined();
      expect(f.operators).toStrictEqual(['is']);
    });

    // The codec writes the `!` negation only for a field that allows exclusion, so offering
    // `is_not` without it gives the user an operator that silently applies as `is`.
    it('should not offer is_not to a field that cannot express it', () => {
      expect(toMatchFieldDef({ key: 'name', label: 'Name' }).operators).toStrictEqual(['is']);
      expect(toMatchFieldDef({ key: 'asset', label: 'Asset', valueType: 'asset' }).operators).toStrictEqual(['is']);
    });

    it('should offer is_not once the field declares exclusion', () => {
      const f = toMatchFieldDef({ allowExclusion: true, key: 'entryTypes', label: 'Type' });

      expect(f.operators).toStrictEqual(['is', 'is_not']);
    });

    it('should keep the range and date defaults, which are not expressed by a prefix', () => {
      expect(toMatchFieldDef({ key: 'amount', label: 'Amount', valueType: 'range' }).operators)
        .toStrictEqual(['between', 'gt', 'lt']);
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
    it('should collapse two amount bounds into a filter-bound range field', () => {
      const f = toRangeFieldDef({ key: 'amount', label: 'Amount', lowerKey: 'minAmount', upperKey: 'maxAmount' });
      expect(f.valueType).toBe('range');
      expect(f.binding).toStrictEqual({ kind: 'filter' });
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
      const field = (valueType: FilterValueType): FieldDef => toMatchFieldDef({ key: 'k', label: 'K', valueType });

      expect(resolveEditor(field('enum'))).toBe('enum');
      expect(resolveEditor(field('asset'))).toBe('asset');
      expect(resolveEditor(field('boolean'))).toBe('boolean');
      expect(resolveEditor(field('range'))).toBe('range');
      expect(resolveEditor(field('date'))).toBe('date');
      // Typed rather than picked, whatever the value type says.
      expect(resolveEditor(toMatchFieldDef({ freeText: true, key: 'k', label: 'K' }))).toBe('text');
    });
  });
});
