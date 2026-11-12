import type { ComputedRef } from 'vue';
import type { AssetPriceInfo } from '@/modules/assets/prices/price-types';
import { type AssetBalanceWithPriceAndChains, type BigNumber, Zero } from '@rotki/common';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useIsHistoryView } from '@/modules/balances/view/balance-view';
import { type AssetComparison, compareByAsset, withQueriedOnlyAssets } from '@/modules/balances/view/history-comparison';
import { useHistoryBalances } from '@/modules/balances/view/use-history-balances';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UseBalanceViewDataReturn {
  readonly isHistory: ComputedRef<boolean>;
  /** History-derived balances exist, so comparisons mean something. */
  readonly comparable: ComputedRef<boolean>;
  /** Asset rows in the page's view. */
  readonly balances: ComputedRef<AssetBalanceWithPriceAndChains[]>;
  /** Liability rows in the page's view. */
  readonly liabilities: ComputedRef<AssetBalanceWithPriceAndChains[]>;
  /** Any liability is held, in either view, so a liabilities table stays put across a switch. */
  readonly liabilitiesHeld: ComputedRef<boolean>;
  /** Net worth in the page's view. */
  readonly netWorth: ComputedRef<BigNumber>;
  readonly queriedNetWorth: Readonly<ComputedRef<BigNumber>>;
  /** History net worth minus queried net worth. */
  readonly netWorthDifference: ComputedRef<BigNumber>;
  /** Manual balances minus manual liabilities: the part of the difference history cannot see. */
  readonly manualNetValue: ComputedRef<BigNumber>;
  /** Per-asset comparison for the dashboard table, with collections folded. */
  readonly comparisons: ComputedRef<Map<string, AssetComparison>>;
  readonly getAssetPriceInfo: (identifier: string, groupCollection?: boolean) => AssetPriceInfo;
  readonly getAssetComparison: (identifier: string, groupCollection?: boolean) => AssetComparison;
}

const NO_COMPARISON: AssetComparison = { delta: Zero, history: Zero, manual: Zero, queried: Zero, valueDelta: Zero };

function sumValues(rows: readonly AssetBalanceWithPriceAndChains[]): BigNumber {
  return rows.reduce((sum, row) => sum.plus(row.value), Zero);
}

function priceInfoOf(rows: readonly AssetBalanceWithPriceAndChains[], identifier: string): AssetPriceInfo {
  const row = rows.find(item => item.asset === identifier);
  return { amount: row?.amount ?? Zero, price: row?.price ?? Zero, value: row?.value ?? Zero };
}

/**
 * The balances, net worth and comparisons of the page's balance view.
 *
 * @remarks
 * Reads the view the enclosing page provided, so it is only ever history on a page that offers the
 * switch. NFTs count toward both net worths when the setting includes them: they are queried-only,
 * so including them on both sides keeps them out of the difference.
 *
 * @param isHistory - the view to read; a page that provides the view passes its own, since a
 * component cannot inject what it provides
 */
export function useBalanceViewData(isHistory: ComputedRef<boolean> = useIsHistoryView()): UseBalanceViewDataReturn {
  const { getBalances, getLiabilities } = useAggregatedBalances();
  const history = useHistoryBalances();
  const { hasData } = storeToRefs(useHistoricalSnapshotStore());
  const { nftValue, totalNetWorth } = storeToRefs(useStatisticsStore());
  const nftsInNetValue = useSetting('nftsInNetValue');

  const historyBalances = computed<AssetBalanceWithPriceAndChains[]>(() => history.getBalances());
  const historyLiabilities = computed<AssetBalanceWithPriceAndChains[]>(() => history.getLiabilities());

  const balances = computed<AssetBalanceWithPriceAndChains[]>(() => (get(isHistory)
    ? withQueriedOnlyAssets(get(historyBalances), getBalances())
    : getBalances()));

  const liabilities = computed<AssetBalanceWithPriceAndChains[]>(() => (get(isHistory) ? get(historyLiabilities) : getLiabilities()));

  const historyNetWorth = computed<BigNumber>(() => sumValues(get(historyBalances))
    .plus(get(nftsInNetValue) ? get(nftValue) : Zero)
    .minus(sumValues(get(historyLiabilities))));

  const netWorth = computed<BigNumber>(() => (get(isHistory) ? get(historyNetWorth) : get(totalNetWorth)));
  const netWorthDifference = computed<BigNumber>(() => get(historyNetWorth).minus(get(totalNetWorth)));
  const manualNetValue = computed<BigNumber>(() => history.getManualNetValue());

  const comparisons = computed<Map<string, AssetComparison>>(() =>
    compareByAsset(get(historyBalances), getBalances(), history.getManualBalances()));

  function getAssetPriceInfo(identifier: string, groupCollection = false): AssetPriceInfo {
    const rows = get(isHistory) ? history.getBalances(groupCollection) : getBalances(true, groupCollection);
    return priceInfoOf(rows, identifier);
  }

  function getAssetComparison(identifier: string, groupCollection = false): AssetComparison {
    return compareByAsset(
      history.getBalances(groupCollection),
      getBalances(true, groupCollection),
      history.getManualBalances(groupCollection),
    ).get(identifier) ?? NO_COMPARISON;
  }

  return {
    balances,
    comparable: hasData,
    comparisons,
    getAssetComparison,
    getAssetPriceInfo,
    isHistory,
    liabilities,
    liabilitiesHeld: computed<boolean>(() => getLiabilities().length > 0),
    manualNetValue,
    netWorth,
    netWorthDifference,
    queriedNetWorth: totalNetWorth,
  };
}
