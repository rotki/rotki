import type { DataTableSortColumn } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { Schema } from 'zod/v4';

export type TableRowKey<T> = keyof T extends string ? keyof T : never;

export type SingleColumnSorting<T extends NonNullable<unknown>> = Required<DataTableSortColumn<T>>;

export type Sorting<T extends NonNullable<unknown>> = SingleColumnSorting<T> | SingleColumnSorting<T>[];

export interface FilterSchema<F, M> {
  filters: Ref<F>;
  matchers: ComputedRef<M[]>;
  RouteFilterSchema?: Schema;
}
