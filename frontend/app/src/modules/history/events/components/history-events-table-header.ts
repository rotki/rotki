import type { DataTableSortData } from '@rotki/ui-library';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';

type SortEntry = Exclude<DataTableSortData<HistoryEventEntry>, undefined | unknown[]>;

/** The columns the events table can be sorted by. */
type SortColumn = NonNullable<SortEntry['column']>;

/** The direction a column falls back to when it has not been sorted yet. */
const DEFAULT_SORT_DIRECTION = 'desc';

/**
 * The sort as an array, whatever shape the table handed over.
 *
 * @remarks
 * `DataTableSortData` is one entry, a list of them, or nothing, and every caller here wants the
 * list form.
 *
 * @param sort - the table's current sort
 * @returns the sort entries, empty when the table is unsorted
 */
export function toSortArray(sort: DataTableSortData<HistoryEventEntry>): SortEntry[] {
  if (Array.isArray(sort))
    return sort;

  return sort ? [sort] : [];
}

/**
 * Whether the table is currently sorted by the given column.
 *
 * @remarks
 * Only the first entry counts: the header offers one sort control, so a multi-column sort set
 * elsewhere reads as sorted by whichever column leads it.
 *
 * @param sort - the table's current sort
 * @param column - the column the header controls
 * @returns the column when it leads the sort, otherwise undefined
 */
export function leadingSortColumn<T extends SortColumn>(
  sort: DataTableSortData<HistoryEventEntry>,
  column: T,
): T | undefined {
  const [first] = toSortArray(sort);
  return first?.column === column ? column : undefined;
}

/** The direction the sort currently runs in, defaulting to descending. */
export function sortDirection(sort: DataTableSortData<HistoryEventEntry>): 'asc' | 'desc' {
  return toSortArray(sort)[0]?.direction ?? DEFAULT_SORT_DIRECTION;
}

/**
 * The sort after the header's control is pressed.
 *
 * @remarks
 * Pressing the column already leading the sort reverses it; pressing any other column starts it
 * descending, which is what a table of events ordered by time is expected to open on.
 *
 * @param sort - the table's current sort
 * @param column - the column that was pressed
 * @returns the replacement sort, as a single-entry array
 */
export function toggledSort(
  sort: DataTableSortData<HistoryEventEntry>,
  column: SortColumn,
): SortEntry[] {
  const [first] = toSortArray(sort);

  if (first?.column !== column)
    return [{ column, direction: DEFAULT_SORT_DIRECTION }];

  return [{ column, direction: first.direction === 'asc' ? 'desc' : 'asc' }];
}

/**
 * How many pages the rows fill.
 *
 * @param total - how many rows there are in all
 * @param perPage - the page size; zero or less yields no pages rather than infinity
 * @returns the page count, never negative or fractional
 */
export function pageCount(total: number, perPage: number): number {
  if (perPage <= 0)
    return 0;

  return Math.ceil(total / perPage);
}
