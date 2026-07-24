import type { Sorting } from '@/modules/core/table/pagination-filter-types';
import { describe, expect, it } from 'vitest';
import { applySortingDefaults, getApiSortingParams, getSorting, parseQueryHistory } from '@/modules/core/table/pagination-filter-utils';

interface EventDetails {
  date: string;
  name: string;
  id: string;
}

describe('use-pagination-filter.utils.ts', () => {
  describe('getApiSortingParams', () => {
    it('should return the default sorting when sorting is an empty array', () => {
      const sorting: Sorting<EventDetails> = [];
      const defaultSorting: Sorting<EventDetails> = [
        { column: 'name', direction: 'asc' },
      ];

      const result = getApiSortingParams(sorting, defaultSorting);

      expect(result).toEqual({
        ascending: [true],
        orderByAttributes: ['name'],
      });
    });

    it('should return the converted default single sorting when defaultSorting is not an array', () => {
      const sorting: Sorting<EventDetails> = [];
      const defaultSorting: Sorting<EventDetails> = { column: 'name', direction: 'asc' };

      const result = getApiSortingParams(sorting, defaultSorting);

      expect(result).toEqual({
        ascending: [true],
        orderByAttributes: ['name'],
      });
    });

    it('should return the converted single column sorting when sorting is a non-array', () => {
      const sorting: Sorting<EventDetails> = { column: 'name', direction: 'asc' };
      const defaultSorting: Sorting<EventDetails> = [
        { column: 'date', direction: 'asc' },
      ];

      const result = getApiSortingParams(sorting, defaultSorting);

      expect(result).toEqual({
        ascending: [true],
        orderByAttributes: ['name'],
      });
    });

    it('should return the converted array sorting when sorting is a non-empty array', () => {
      const sorting: Sorting<EventDetails> = [
        { column: 'date', direction: 'asc' },
        { column: 'name', direction: 'desc' },
      ];
      const defaultSorting: Sorting<EventDetails> = { column: 'id', direction: 'desc' };

      const result = getApiSortingParams(sorting, defaultSorting);

      expect(result).toEqual({
        ascending: [true, false],
        orderByAttributes: ['date', 'name'],
      });
    });
  });

  describe('fallbackColumn', () => {
    it('should fall back to timestamp when no fallback column is given', () => {
      expect(applySortingDefaults<EventDetails>(undefined)).toEqual({
        column: 'timestamp',
        direction: 'desc',
      });
      expect(getSorting<EventDetails>({})).toEqual({
        column: 'timestamp',
        direction: 'desc',
      });
    });

    it('should use the given fallback column instead of timestamp', () => {
      expect(applySortingDefaults<EventDetails>(undefined, 'name')).toEqual({
        column: 'name',
        direction: 'desc',
      });
      expect(getSorting<EventDetails>({}, undefined, 'name')).toEqual({
        column: 'name',
        direction: 'desc',
      });
    });

    it('should apply the fallback only to entries that name no column', () => {
      const result = applySortingDefaults<EventDetails>([
        { column: 'date', direction: 'asc' },
        { column: undefined, direction: 'desc' },
      ], 'name');

      expect(result).toEqual([
        { column: 'date', direction: 'asc' },
        { column: 'name', direction: 'desc' },
      ]);
    });

    it('should prefer explicit defaults over the fallback column', () => {
      expect(getSorting<EventDetails>({}, { column: 'id' }, 'name')).toEqual({
        column: 'id',
        direction: 'desc',
      });
    });
  });

  describe('parseQueryHistory', () => {
    it('should return the defaults when the query has no sort or order', () => {
      const defaults: Sorting<EventDetails> = { column: 'name', direction: 'asc' };
      expect(parseQueryHistory<EventDetails>({}, defaults)).toBe(defaults);
    });

    it('should parse a single-column sort from the query when the default is not an array', () => {
      const defaults: Sorting<EventDetails> = { column: 'name', direction: 'asc' };
      expect(parseQueryHistory<EventDetails>({ sort: 'date', sortOrder: 'desc' }, defaults)).toEqual({
        column: 'date',
        direction: 'desc',
      });
    });

    it('should parse multiple sort columns when the default is an array', () => {
      const defaults: Sorting<EventDetails> = [{ column: 'name', direction: 'asc' }];
      expect(parseQueryHistory<EventDetails>({ sort: ['date', 'name'], sortOrder: ['asc', 'desc'] }, defaults)).toEqual([
        { column: 'date', direction: 'asc' },
        { column: 'name', direction: 'desc' },
      ]);
    });

    it('should apply the fallback column to multi-sort entries missing a column', () => {
      const defaults: Sorting<EventDetails> = [{ column: 'name', direction: 'asc' }];
      expect(parseQueryHistory<EventDetails>({ sortOrder: ['asc', 'desc'] }, defaults, 'id')).toEqual([
        { column: 'id', direction: 'asc' },
        { column: 'id', direction: 'desc' },
      ]);
    });
  });
});
