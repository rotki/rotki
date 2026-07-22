import { describe, expect, it } from 'vitest';
import {
  CommaSeparatedStringSchema,
  HistoryPaginationSchema,
  HistorySortOrderSchema,
  RouterAccountsSchema,
  RouterExpandedIdsSchema,
  RouterLocationLabelsSchema,
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
});
