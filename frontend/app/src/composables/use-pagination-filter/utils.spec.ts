import type { Sorting } from '@/composables/use-pagination-filter/types';
import { describe, expect, it } from 'vitest';
import { getApiSortingParams } from '@/composables/use-pagination-filter/utils';

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
});
