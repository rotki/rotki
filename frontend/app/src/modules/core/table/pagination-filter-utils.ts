import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { SingleColumnSorting, Sorting, TableRowKey } from '@/modules/core/table/pagination-filter-types';
import { transformCase } from '@rotki/common';
import { HistoryPaginationSchema, HistorySortOrderSchema, type LocationQuery } from '@/modules/core/table/route';

interface ApiSorting {
  orderByAttributes: string[];
  ascending: boolean[];
}

/** The column every table falls back to when neither the state nor the defaults name one. */
export const DEFAULT_FALLBACK_SORT_COLUMN = 'timestamp';

export function getSorting<T extends NonNullable<unknown>>(
  sorting: { column?: string; direction?: 'asc' | 'desc' },
  defaults?: { column?: string; direction?: 'asc' | 'desc' },
  fallbackColumn: string = DEFAULT_FALLBACK_SORT_COLUMN,
): SingleColumnSorting<T> {
  const {
    column = defaults?.column || fallbackColumn,
    direction = defaults?.direction || 'desc',
  } = sorting;
  return {
    column: column as TableRowKey<T>,
    direction,
  };
}

function parseMultiSort<T extends NonNullable<unknown>>(
  sort: string[] | undefined,
  order: ('asc' | 'desc')[] | undefined,
  fallbackColumn: string,
): SingleColumnSorting<T>[] {
  const length = sort?.length || order?.length || 0;
  const sorting: SingleColumnSorting<T>[] = [];

  for (let i = 0; i < length; i++) {
    sorting.push(getSorting({
      column: sort?.[i],
      direction: order?.[i],
    }, undefined, fallbackColumn));
  }

  return sorting;
}

export function parseQueryHistory<T extends NonNullable<unknown>>(
  query: LocationQuery,
  defaults: Sorting<T>,
  fallbackColumn: string = DEFAULT_FALLBACK_SORT_COLUMN,
): Sorting<T> {
  const { sort, sortOrder: order } = HistorySortOrderSchema.parse(query);

  if (!sort && !order)
    return defaults;

  if (!Array.isArray(defaults)) {
    return getSorting({
      column: sort?.[0],
      direction: order?.[0],
    }, defaults, fallbackColumn);
  }

  return parseMultiSort<T>(sort, order, fallbackColumn);
}

export function parseQueryPagination(query: LocationQuery, pagination: TablePaginationData): TablePaginationData {
  const { limit, page } = HistoryPaginationSchema.parse(query);

  return {
    ...pagination,
    ...(page ? { page } : {}),
    ...(limit ? { limit } : {}),
  } satisfies TablePaginationData;
}

export function applySortingDefaults<T extends NonNullable<unknown>>(
  sorting: DataTableSortData<T>,
  fallbackColumn: string = DEFAULT_FALLBACK_SORT_COLUMN,
): Sorting<T> {
  const defaultColumn = fallbackColumn as TableRowKey<T>;
  const defaultDirection = 'desc';
  if (!sorting) {
    return {
      column: defaultColumn,
      direction: defaultDirection,
    };
  }
  else if (Array.isArray(sorting)) {
    return sorting.map(item => ({
      column: item.column ?? defaultColumn,
      direction: item.direction,
    }));
  }
  else {
    return {
      column: sorting.column ?? defaultColumn,
      direction: sorting.direction,
    };
  }
}

export function applyPaginationDefaults(limit: number): TablePaginationData {
  return {
    limit,
    page: 1,
    total: -1,
  };
}

function arrayToApiSorting<T extends NonNullable<unknown>>(sorting: SingleColumnSorting<T>[]): ApiSorting {
  return {
    ascending: sorting.map(item => item.direction === 'asc'),
    orderByAttributes: sorting.map(item => transformCase(item.column)),
  };
}

function singleToApiSorting<T extends NonNullable<unknown>>(sorting: SingleColumnSorting<T>): ApiSorting {
  return {
    ascending: [sorting.direction === 'asc'],
    orderByAttributes: sorting.column ? [transformCase(sorting.column)] : [],
  };
}

export function getApiSortingParams<T extends NonNullable<unknown>>(
  sorting: Sorting<T>,
  defaultSorting: Sorting<T>,
): ApiSorting {
  if (Array.isArray(sorting)) {
    if (sorting.length === 0) {
      if (Array.isArray(defaultSorting)) {
        return arrayToApiSorting(defaultSorting);
      }
      else {
        return singleToApiSorting(defaultSorting);
      }
    }
    else {
      return arrayToApiSorting(sorting);
    }
  }
  else {
    return singleToApiSorting(sorting);
  }
}
