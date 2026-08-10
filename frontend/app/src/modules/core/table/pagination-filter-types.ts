import type { DataTableSortColumn } from '@rotki/ui-library';
import type { Ref } from 'vue';

export type TableRowKey<T> = keyof T extends string ? keyof T : never;

export type SingleColumnSorting<T extends NonNullable<unknown>> = Required<DataTableSortColumn<T>>;

export type Sorting<T extends NonNullable<unknown>> = SingleColumnSorting<T> | SingleColumnSorting<T>[];

/**
 * A table's filter bag. The url shape of the bag and the keys the request wraps as
 * `{ behaviour, values }` used to be declared here too; both are now read off the table's fields
 * (`routeSchemaFromFields`, `behaviourKeysFromFields`), which already state them.
 */
export interface FilterSchema<F> {
  filters: Ref<F>;
}
