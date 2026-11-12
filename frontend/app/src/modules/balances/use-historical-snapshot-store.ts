import type { ComputedRef, Ref, ShallowRef } from 'vue';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';

interface HistoricalSnapshot {
  entries: HistoricalBalanceEntry[];
  processingRequired: boolean;
  stale: boolean;
}

interface UseHistoricalSnapshotStoreReturn {
  entries: ShallowRef<HistoricalBalanceEntry[]>;
  loading: Ref<boolean>;
  error: Ref<string | undefined>;
  processingRequired: Ref<boolean>;
  stale: Ref<boolean>;
  loaded: Ref<boolean>;
  /**
   * The snapshot holds history-derived balances to show.
   *
   * @remarks
   * An empty snapshot means history was never processed, or there are no history events at all;
   * reading it as a portfolio worth nothing would be wrong, so the history view and every
   * comparison wait for this.
   */
  hasData: ComputedRef<boolean>;
  setSnapshot: (snapshot: HistoricalSnapshot) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | undefined) => void;
}

/**
 * The current history-derived balances, as last fetched.
 *
 * @remarks
 * State-only and synchronous: `useCurrentHistoricalBalances` does the fetching. Which balances a page
 * shows is not stored here; it lives in the page's route query (see `useBalanceView`), so nothing
 * outside a page that opted in can be switched by it.
 */
export const useHistoricalSnapshotStore = defineStore('balances/historical-snapshot', (): UseHistoricalSnapshotStoreReturn => {
  const entries = shallowRef<HistoricalBalanceEntry[]>([]);
  const loading = ref<boolean>(false);
  const error = ref<string>();
  const processingRequired = ref<boolean>(false);
  const stale = ref<boolean>(false);
  const loaded = ref<boolean>(false);

  const hasData = computed<boolean>(() => get(loaded) && get(entries).length > 0);

  function setSnapshot(snapshot: HistoricalSnapshot): void {
    set(entries, snapshot.entries);
    set(processingRequired, snapshot.processingRequired);
    set(stale, snapshot.stale);
    set(loaded, true);
  }

  function setLoading(value: boolean): void {
    set(loading, value);
  }

  function setError(value: string | undefined): void {
    set(error, value);
  }

  return {
    entries,
    error,
    hasData,
    loaded,
    loading,
    processingRequired,
    setError,
    setLoading,
    setSnapshot,
    stale,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalSnapshotStore, import.meta.hot));
