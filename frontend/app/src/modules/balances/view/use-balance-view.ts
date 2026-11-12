import type { ComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import { useCurrentHistoricalBalances } from '@/modules/balances/use-current-historical-balances';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { BALANCE_VIEW_QUERY, BalanceView } from '@/modules/balances/view/balance-view';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { usePremium } from '@/modules/premium/use-premium';

interface UseBalanceViewReturn {
  /** The history view can be offered: the accounting update is on and the user has premium. */
  readonly available: ComputedRef<boolean>;
  /** The page shows history-derived balances. */
  readonly isHistory: ComputedRef<boolean>;
  /** History-derived balances exist to show; until then the history view cannot be picked. */
  readonly historyReady: ComputedRef<boolean>;
  readonly view: ComputedRef<BalanceView>;
  readonly setView: (view: BalanceView) => Promise<void>;
}

/**
 * The balance view of the current page, read from and written to its route query.
 *
 * @remarks
 * The current history-derived balances are premium-only, so the view is only offered to premium
 * users; a `view=history` query without premium reads as queried, as does one before history has
 * been processed, so the page never shows an empty snapshot as a portfolio worth nothing. While the
 * view is available the snapshot is loaded once, which the comparison lines need even in the
 * queried view.
 */
export function useBalanceView(): UseBalanceViewReturn {
  const route = useRoute();
  const router = useRouter();
  const premium = usePremium();
  const enabled = isAccountingUpdateEnabled();
  const snapshot = enabled ? useCurrentHistoricalBalances() : undefined;

  const { hasData: historyReady } = storeToRefs(useHistoricalSnapshotStore());

  const available = computed<boolean>(() => enabled && get(premium));
  const isHistory = computed<boolean>(() =>
    get(available) && get(historyReady) && get(route).query[BALANCE_VIEW_QUERY] === BalanceView.HISTORY);
  const view = computed<BalanceView>(() => (get(isHistory) ? BalanceView.HISTORY : BalanceView.QUERIED));

  async function setView(next: BalanceView): Promise<void> {
    const query = { ...get(route).query };
    if (next === BalanceView.HISTORY)
      query[BALANCE_VIEW_QUERY] = BalanceView.HISTORY;
    else
      delete query[BALANCE_VIEW_QUERY];
    await router.replace({ query });
  }

  watch(available, (isAvailable) => {
    if (isAvailable && snapshot)
      startPromise(snapshot.ensureLoaded());
  }, { immediate: true });

  return { available, historyReady, isHistory, setView, view };
}
