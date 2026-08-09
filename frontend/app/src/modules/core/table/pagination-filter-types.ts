import type { DataTableSortColumn } from '@rotki/ui-library';
import type { Ref } from 'vue';
import type { Schema } from 'zod';

export type TableRowKey<T> = keyof T extends string ? keyof T : never;

export type SingleColumnSorting<T extends NonNullable<unknown>> = Required<DataTableSortColumn<T>>;

export type Sorting<T extends NonNullable<unknown>> = SingleColumnSorting<T> | SingleColumnSorting<T>[];

export interface FilterSchema<F> {
  filters: Ref<F>;
  RouteFilterSchema?: Schema;
  /**
   * Wire keys the backend takes as `{ behaviour, values }` rather than a bare list (its
   * `IncludeExcludeListField` requires the wrapper and rejects a plain list), so an excluded value
   * can be expressed. The pill codec writes exclusion as a `!` prefix, which is also what the URL
   * carries; the wrapping happens at request assembly, where this is read.
   *
   * Declared per table: it describes the request. Typed against the filter's own keys so a key
   * that is not one of them fails to compile.
   */
  behaviourKeys?: readonly (keyof F & string)[];
}
