import { HistoryPaginationSchema, HistorySortOrderSchema, type LocationQuery } from '@/types/route';
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { SingleColumnSorting, Sorting, TableRowKey } from '@/composables/use-pagination-filter/types';

function getSorting<T extends NonNullable<unknown>>(
  sorting: { column?: string; direction?: 'asc' | 'desc' },
): SingleColumnSorting<T> {
  const {
    column = 'timestamp',
    direction = 'desc',
  } = sorting;
  return {
    column: column as TableRowKey<T>,
    direction,
  };
}

export function parseQueryHistory<T extends NonNullable<unknown>>(query: LocationQuery, defaults: Sorting<T>): Sorting<T> {
  const singleSort = !Array.isArray(defaults);
  const sorting = HistorySortOrderSchema.parse(query);

  const sort = sorting.sort;
  const order = sorting.sortOrder;
  if (!sort && !order) {
    return defaults;
  }

  if (singleSort) {
    return getSorting({
      column: sort?.[0],
      direction: order?.[0],
    });
  }
  else {
    const length = sort?.length || order?.length || 0;
    const sorting: SingleColumnSorting<T>[] = [];

    for (let i = 0; i < length; i++) {
      sorting.push(getSorting({
        column: sort?.[i],
        direction: order?.[i],
      }));
    }

    return sorting;
  }
}

export function parseQueryPagination(query: LocationQuery, pagination: TablePaginationData): TablePaginationData {
  const { page, limit } = HistoryPaginationSchema.parse(query);

  return {
    ...pagination,
    ...(page ? { page } : {}),
    ...(limit ? { limit } : {}),
  } satisfies TablePaginationData;
}

export function applySortingDefaults<T extends NonNullable<unknown>>(sorting: DataTableSortData<T>): Sorting<T> {
  const defaultColumn = 'timestamp' as TableRowKey<T>;
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
    page: 1,
    limit,
    total: -1,
  };
}

export function getApiSortingParams<T extends NonNullable<unknown>>(sorting: Sorting<T>): { orderByAttributes: string[]; ascending: boolean[] } {
  if (Array.isArray(sorting)) {
    if (sorting.length === 0) {
      return {
        orderByAttributes: ['timestamp'],
        ascending: [false],
      };
    }
    else {
      return {
        orderByAttributes: sorting.map(item => transformCase(item.column)),
        ascending: sorting.map(item => item.direction === 'asc'),
      };
    }
  }
  else {
    return {
      orderByAttributes: [transformCase(sorting.column)],
      ascending: [sorting.direction === 'asc'],
    };
  }
}
