import type { ComputedRef, InjectionKey, MaybeRef, MaybeRefOrGetter, Ref } from 'vue';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';

const TableFetchErrorKey: InjectionKey<Ref<unknown>> = Symbol('table-fetch-error');

/** The text `RuiDataTable` renders in place of rows when a table has none. */
export interface TableEmptyState {
  label?: string;
  description?: string;
}

interface TableEmptyStateOptions {
  /**
   * The failure to report, when the table cannot inject one.
   *
   * @remarks
   * Needed where the fetch is owned by a `createSharedComposable`: the provide there would bind to
   * whichever component instantiated the singleton first, which is not the one rendering the rows.
   */
  error?: MaybeRef<unknown>;
  /** The empty text to use while there is no failure. Defaults to the generic "no data". */
  fallback?: MaybeRefOrGetter<TableEmptyState>;
}

/**
 * Shares a server table's last fetch failure with the component that renders its rows.
 *
 * @remarks
 * The fetch is owned by the view but the failure is only ever read at the leaf, often two or three
 * components down, so it is provided rather than threaded through every wrapper in between. A table
 * that does not want it simply never injects.
 */
export function provideTableFetchError(error: Ref<unknown>): void {
  if (getCurrentInstance())
    provide(TableFetchErrorKey, error);
}

/**
 * A table's empty text, replaced by the reason its last fetch failed.
 *
 * @remarks
 * A failed read leaves the collection empty, so a table that could not reach the backend renders
 * exactly like one the user genuinely has no rows for. Since rotki#12942 the read's notification is
 * `NORMAL` and no longer pops, which leaves the table itself as the only place the reason appears.
 */
export function useTableEmptyState(options: TableEmptyStateOptions = {}): ComputedRef<TableEmptyState> {
  const { error, fallback } = options;
  const provided = inject(TableFetchErrorKey, undefined);
  const { t } = useI18n({ useScope: 'global' });

  return computed<TableEmptyState>(() => {
    const source = error ?? provided;
    const failure = source ? get(source) : undefined;

    if (!failure)
      return toValue(fallback) ?? { description: t('data_table.no_data') };

    return {
      description: getErrorMessage(failure),
      label: t('data_table.fetch_failed'),
    };
  });
}
