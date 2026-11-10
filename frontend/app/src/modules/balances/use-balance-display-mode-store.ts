import type { ComputedRef, Ref, ShallowRef } from 'vue';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';

/** Which balances the portfolio surfaces display. */
export type BalanceDisplayMode = 'queried' | 'history';

interface UseBalanceDisplayModeStoreReturn {
  mode: Ref<BalanceDisplayMode>;
  /** Whether history-derived balances should be shown; always false when the feature is off. */
  isHistoryMode: ComputedRef<boolean>;
  entries: ShallowRef<HistoricalBalanceEntry[]>;
  loading: Ref<boolean>;
  error: Ref<string | undefined>;
  processingRequired: Ref<boolean>;
  stale: Ref<boolean>;
  loaded: Ref<boolean>;
  setMode: (mode: BalanceDisplayMode) => void;
  setSnapshot: (snapshot: {
    entries: HistoricalBalanceEntry[];
    processingRequired: boolean;
    stale: boolean;
  }) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | undefined) => void;
  reset: () => void;
}

/**
 * Session-scoped state for the balance display mode and the current history-derived snapshot.
 *
 * @remarks
 * State-only and synchronous: the async fetching that populates `entries` lives in
 * `useCurrentHistoricalBalances`. `mode` defaults to `queried` per session and is forced back to
 * `queried` when the accounting update is disabled, so a build without the feature never shows
 * balances derived from a pipeline that is not running.
 */
export const useBalanceDisplayModeStore = defineStore('balances/display-mode', (): UseBalanceDisplayModeStoreReturn => {
  const mode = ref<BalanceDisplayMode>('queried');
  const entries = shallowRef<HistoricalBalanceEntry[]>([]);
  const loading = ref<boolean>(false);
  const error = ref<string | undefined>();
  const processingRequired = ref<boolean>(false);
  const stale = ref<boolean>(false);
  const loaded = ref<boolean>(false);

  /** The single source of truth every consumer reads; false whenever the feature is off. */
  const isHistoryMode = computed<boolean>(() => isAccountingUpdateEnabled() && get(mode) === 'history');

  function setMode(newMode: BalanceDisplayMode): void {
    set(mode, isAccountingUpdateEnabled() ? newMode : 'queried');
  }

  function setSnapshot(snapshot: {
    entries: HistoricalBalanceEntry[];
    processingRequired: boolean;
    stale: boolean;
  }): void {
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

  function reset(): void {
    set(mode, 'queried');
    set(entries, []);
    set(loading, false);
    set(error, undefined);
    set(processingRequired, false);
    set(stale, false);
    set(loaded, false);
  }

  return {
    entries,
    error,
    isHistoryMode,
    loaded,
    loading,
    mode,
    processingRequired,
    reset,
    setError,
    setLoading,
    setMode,
    setSnapshot,
    stale,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalanceDisplayModeStore, import.meta.hot));
