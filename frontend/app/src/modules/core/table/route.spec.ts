import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { describe, expect, it } from 'vitest';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { toMatchFieldDef, toParamFieldDef, toRangeFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import {
  behaviourKeysFromFields,
  CommaSeparatedStringSchema,
  HistoryPaginationSchema,
  HistorySortOrderSchema,
  RouterAccountsSchema,
  RouterExpandedIdsSchema,
  RouterLocationLabelsSchema,
  routeSchemaFromFields,
} from '@/modules/core/table/route';

describe('route query schemas', () => {
  describe('commaSeparatedStringSchema', () => {
    it('should split a comma separated string', () => {
      expect(CommaSeparatedStringSchema.parse('a,b,c')).toStrictEqual(['a', 'b', 'c']);
    });

    it('should return an empty array when absent', () => {
      expect(CommaSeparatedStringSchema.parse(undefined)).toStrictEqual([]);
    });
  });

  describe('routerExpandedIdsSchema', () => {
    it('should read the expanded ids off the query', () => {
      expect(RouterExpandedIdsSchema.parse({ expanded: '1,2' })).toStrictEqual({ expanded: ['1', '2'] });
    });
  });

  describe('historySortOrderSchema', () => {
    it('should arrayify single sort values', () => {
      expect(HistorySortOrderSchema.parse({ sort: 'timestamp', sortOrder: 'asc' }))
        .toStrictEqual({ sort: ['timestamp'], sortOrder: ['asc'] });
    });

    it('should keep array sort values', () => {
      expect(HistorySortOrderSchema.parse({ sort: ['a', 'b'], sortOrder: ['asc', 'desc'] }))
        .toStrictEqual({ sort: ['a', 'b'], sortOrder: ['asc', 'desc'] });
    });

    it('should leave omitted values out of the result', () => {
      expect(HistorySortOrderSchema.parse({})).toStrictEqual({});
    });

    it('should reject an invalid sort order', () => {
      expect(() => HistorySortOrderSchema.parse({ sortOrder: 'sideways' })).toThrow();
    });
  });

  describe('historyPaginationSchema', () => {
    it('should coerce numeric strings', () => {
      expect(HistoryPaginationSchema.parse({ limit: '10', page: '3' })).toStrictEqual({ limit: 10, page: 3 });
    });

    it('should default the page to 1', () => {
      expect(HistoryPaginationSchema.parse({ limit: '25' })).toStrictEqual({ limit: 25, page: 1 });
    });

    it('should reject a page below 1', () => {
      expect(() => HistoryPaginationSchema.parse({ page: '0' })).toThrow();
    });
  });

  describe('routerLocationLabelsSchema', () => {
    it('should split a comma separated single value', () => {
      expect(RouterLocationLabelsSchema.parse({ locationLabels: '0xaaa,0xbbb' }))
        .toStrictEqual({ locationLabels: ['0xaaa', '0xbbb'] });
    });

    it('should flatten an array of comma separated values', () => {
      expect(RouterLocationLabelsSchema.parse({ locationLabels: ['0xaaa,0xbbb', '0xccc'] }))
        .toStrictEqual({ locationLabels: ['0xaaa', '0xbbb', '0xccc'] });
    });

    it('should leave omitted labels out of the result', () => {
      expect(RouterLocationLabelsSchema.parse({})).toStrictEqual({});
    });
  });

  describe('routerAccountsSchema', () => {
    it('should parse an address#chain pair', () => {
      expect(RouterAccountsSchema.parse({ accounts: '0xaaa#eth' }))
        .toStrictEqual({ accounts: [{ address: '0xaaa', chain: 'eth' }] });
    });

    it('should accept the ALL chain sentinel', () => {
      expect(RouterAccountsSchema.parse({ accounts: '0xaaa#ALL' }))
        .toStrictEqual({ accounts: [{ address: '0xaaa', chain: 'ALL' }] });
    });

    it('should skip entries without a chain separator', () => {
      expect(RouterAccountsSchema.parse({ accounts: '0xaaa' })).toStrictEqual({ accounts: [] });
    });

    it('should skip entries with an unknown chain', () => {
      expect(RouterAccountsSchema.parse({ accounts: '0xaaa#notachain' })).toStrictEqual({ accounts: [] });
    });
  });

  describe('routeSchemaFromFields', () => {
    const single: FieldDef = toMatchFieldDef({ key: 'location', label: 'Location', multiple: false });
    const many: FieldDef = toMatchFieldDef({ key: 'counterparties', label: 'Protocol', multiple: true });

    it('should read a single-value field as one optional string', () => {
      expect(routeSchemaFromFields([single]).parse({ location: 'kraken' })).toStrictEqual({ location: 'kraken' });
    });

    it('should read a multi-value field as a list, however the url spells it', () => {
      const schema = routeSchemaFromFields([many]);

      expect(schema.parse({ counterparties: 'uniswap-v2' })).toStrictEqual({ counterparties: ['uniswap-v2'] });
      expect(schema.parse({ counterparties: ['uniswap-v2', 'curve'] }))
        .toStrictEqual({ counterparties: ['uniswap-v2', 'curve'] });
    });

    it('should expand a bounds field into its two wire keys and leave its own key out, since a collapsed pill key is a display name rather than a wire one', () => {
      const amount = toRangeFieldDef({ key: 'amount', label: 'Amount', lowerKey: 'minAmount', upperKey: 'maxAmount' });

      expect(routeSchemaFromFields([amount]).parse({ amount: '5', maxAmount: '10', minAmount: '1' }))
        .toStrictEqual({ maxAmount: '10', minAmount: '1' });
    });

    it('should leave a param-bound field out of the filter bag, its own source reading it back', () => {
      const owned = toParamFieldDef({
        key: 'owned',
        label: 'Owned',
        paramKey: 'showUserOwnedAssetsOnly',
        to: 'both',
        valueType: FilterValueTypes.BOOLEAN,
      });

      expect(routeSchemaFromFields([owned]).parse({ owned: 'true' })).toStrictEqual({});
    });

    it('should allow an empty query', () => {
      expect(routeSchemaFromFields([single, many]).parse({})).toStrictEqual({});
    });
  });

  describe('behaviourKeysFromFields', () => {
    it('should name the fields that can express an exclusion', () => {
      const fields = [
        toMatchFieldDef({ allowExclusion: true, key: 'entryTypes', label: 'Type', multiple: true }),
        toMatchFieldDef({ key: 'location', label: 'Location', multiple: false }),
      ];

      expect(behaviourKeysFromFields(fields)).toStrictEqual(['entryTypes']);
    });

    it('should never name a param-bound field, a param having no form for the `!` negation', () => {
      const state = toParamFieldDef({ key: 'state', label: 'State', paramKey: 'stateMarkers', to: 'request' });

      expect(behaviourKeysFromFields([state])).toStrictEqual([]);
    });
  });
});
