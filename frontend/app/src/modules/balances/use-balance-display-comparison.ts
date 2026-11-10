import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { startPromise } from '@shared/utils';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalanceDisplayModeStore } from '@/modules/balances/use-balance-display-mode-store';
import { useCurrentHistoricalBalances } from '@/modules/balances/use-current-historical-balances';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';

interface BalanceDisplayComparison {
  /** Whether the comparison line should be shown at all. */
  readonly show: ComputedRef<boolean>;
  /** The amount under the mode the user is NOT currently viewing. */
  readonly comparisonAmount: ComputedRef<BigNumber>;
  /** The amount under the mode the user is currently viewing. */
  readonly activeAmount: ComputedRef<BigNumber>;
  /** The active amount minus the comparison amount; zero when the two agree. */
  readonly delta: ComputedRef<BigNumber>;
  /** Whether the two modes disagree on this asset's amount. */
  readonly hasDiscrepancy: ComputedRef<boolean>;
}

/**
 * The amounts of one asset under both balance display modes, for a side-by-side comparison.
 *
 * @remarks
 * Reads both modes independently of the active one, so switching mode never compares a value to
 * itself. Hidden entirely when the accounting update is off or before history balances are loaded,
 * since a missing snapshot would otherwise read as a zero balance and a false discrepancy.
 *
 * @param identifier - the asset whose amounts are compared
 * @param groupCollection - fold collection members into the parent's amount
 */
export function useBalanceDisplayComparison(
  identifier: MaybeRefOrGetter<string>,
  groupCollection: MaybeRefOrGetter<boolean> = false,
): BalanceDisplayComparison {
  const { isHistoryMode, loaded } = storeToRefs(useBalanceDisplayModeStore());
  const { getQueriedAssetPriceInfo, getHistoryAssetPriceInfo } = useAggregatedBalances();

  const enabled = isAccountingUpdateEnabled();

  // Shared with the switch: loads the snapshot once so a queried-mode comparison has data.
  if (enabled)
    startPromise(useCurrentHistoricalBalances().ensureLoaded());

  const queriedAmount = computed<BigNumber>(() =>
    getQueriedAssetPriceInfo(toValue(identifier), toValue(groupCollection)).amount);
  const historyAmount = computed<BigNumber>(() =>
    getHistoryAssetPriceInfo(toValue(identifier), toValue(groupCollection)).amount);

  const activeAmount = computed<BigNumber>(() =>
    get(isHistoryMode) ? get(historyAmount) : get(queriedAmount));
  const comparisonAmount = computed<BigNumber>(() =>
    get(isHistoryMode) ? get(queriedAmount) : get(historyAmount));

  const delta = computed<BigNumber>(() => get(activeAmount).minus(get(comparisonAmount)));
  const hasDiscrepancy = computed<boolean>(() => !get(delta).isZero());
  const show = computed<boolean>(() => enabled && get(loaded));

  return {
    activeAmount,
    comparisonAmount,
    delta,
    hasDiscrepancy,
    show,
  };
}
