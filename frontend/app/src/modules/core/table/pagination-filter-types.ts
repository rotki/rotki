import type { DataTableSortColumn } from '@rotki/ui-library';

export type TableRowKey<T> = keyof T extends string ? keyof T : never;

export type SingleColumnSorting<T extends NonNullable<unknown>> = Required<DataTableSortColumn<T>>;

export type Sorting<T extends NonNullable<unknown>> = SingleColumnSorting<T> | SingleColumnSorting<T>[];
