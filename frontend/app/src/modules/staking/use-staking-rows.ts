import type { ComputedRef, Ref } from 'vue';

interface UseStakingRowsOptions<TResponse, TRow, TTotal> {
  /** Queries the backend for the positions of every tracked account. */
  fetch: () => Promise<TResponse>;
  /** Flattens the response into table rows. */
  toRows: (response: TResponse) => TRow[];
  /** Aggregates the rows into the figure shown above the table. */
  toTotal: (rows: TRow[]) => TTotal;
}

export interface UseStakingRowsReturn<TRow, TTotal> {
  error: Readonly<Ref<string>>;
  loading: Readonly<Ref<boolean>>;
  refresh: () => Promise<void>;
  rows: ComputedRef<TRow[]>;
  total: ComputedRef<TTotal>;
}

/**
 * Loads the staking positions of a chain and exposes them as table rows with a total.
 *
 * @remarks
 * A failed query keeps the rows of the last successful one and reports the failure through
 * `error`, so a flaky backend does not blank a table the user was reading.
 */
export function useStakingRows<TResponse, TRow, TTotal>(
  { fetch, toRows, toTotal }: UseStakingRowsOptions<TResponse, TRow, TTotal>,
): UseStakingRowsReturn<TRow, TTotal> {
  const rows = shallowRef<TRow[]>([]);
  const loading = shallowRef<boolean>(false);
  const error = shallowRef<string>('');

  const total = computed<TTotal>(() => toTotal(get(rows)));

  async function refresh(): Promise<void> {
    set(loading, true);
    set(error, '');
    try {
      set(rows, toRows(await fetch()));
    }
    catch (error_: unknown) {
      set(error, error_ instanceof Error ? error_.message : String(error_));
    }
    finally {
      set(loading, false);
    }
  }

  return {
    error: readonly(error),
    loading: readonly(loading),
    refresh,
    rows: computed<TRow[]>(() => get(rows)),
    total,
  };
}
