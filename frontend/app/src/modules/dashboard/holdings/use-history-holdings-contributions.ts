import type { ComputedRef } from 'vue';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { type BigNumber, NoPrice, Zero } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { useIsHistoryView } from '@/modules/balances/view/balance-view';
import { useHistoryBalances } from '@/modules/balances/view/use-history-balances';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN } from '@/modules/core/common/defaults';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { type SourceContribution, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { mergeLocations } from '@/modules/dashboard/holdings/core/location-holdings';
import { type HoldingsInputs, useHoldingsContributions } from '@/modules/dashboard/holdings/use-holdings-contributions';

/** Chain and exchange contributions from history buckets, one per chain or exchange location. */
function useDerivedContributions(): ComputedRef<SourceContribution[]> {
  const { entries } = storeToRefs(useHistoricalSnapshotStore());
  const { isAssetIgnored } = useAssetsStore();
  const { getAssetPrice } = usePriceUtils();
  const resolveIdentifier = useResolveAssetIdentifier();
  const { matchChain } = useSupportedChains();

  function valueOf(entry: HistoricalBalanceEntry): BigNumber {
    const price = getAssetPrice(resolveIdentifier(entry.asset), NoPrice);
    return price.gt(0) ? entry.amount.multipliedBy(price) : Zero;
  }

  return computed<SourceContribution[]>(() => {
    const byChain = new Map<string, BigNumber>();
    const byLocation = new Map<string, BigNumber>();
    for (const entry of get(entries)) {
      if (isAssetIgnored(resolveIdentifier(entry.asset)) || entry.location === TRADE_LOCATION_BANKS)
        continue;

      const chain = matchChain(entry.location) ?? (entry.location === TRADE_LOCATION_BLOCKCHAIN ? TRADE_LOCATION_BLOCKCHAIN : undefined);
      const totals = chain === undefined ? byLocation : byChain;
      const key = chain ?? entry.location;
      totals.set(key, (totals.get(key) ?? Zero).plus(valueOf(entry)));
    }
    return [
      ...Array.from(byChain, ([chain, value]): SourceContribution => ({ chain, kind: SourceKind.BLOCKCHAIN, loading: false, value })),
      ...Array.from(byLocation, ([location, value]): SourceContribution => ({ kind: SourceKind.EXCHANGE, loading: false, location, value })),
    ];
  });
}

/** How one source kind differs between the history view and the queried view. */
export interface SourceDifference {
  readonly kind: SourceKind;
  /** History value minus queried value, in the main currency. */
  readonly delta: BigNumber;
  /** `derived` from history events, carried through `queried`, or `excluded` from history. */
  readonly basis: 'derived' | 'queried' | 'excluded';
}

const DERIVED_KINDS: readonly SourceKind[] = [SourceKind.BLOCKCHAIN, SourceKind.EXCHANGE];

function totalOf(contributions: readonly SourceContribution[], kind: SourceKind): BigNumber {
  return bigNumberSum(contributions.filter(contribution => contribution.kind === kind).map(({ value }) => value));
}

/**
 * Per source kind, how far the history view is from the queried one.
 *
 * @remarks
 * Chains and exchanges are derived, so their difference is a real mismatch. Banks are queried in
 * both views, so theirs is zero. Manual balances are not in history, so their whole value is a gap.
 * Kinds held in neither view are left out.
 */
export function useSourceDifferences(): ComputedRef<SourceDifference[]> {
  const queried = useHoldingsContributions();
  const derived = useDerivedContributions();

  return computed<SourceDifference[]>(() => {
    const queriedRows = get(queried.contributions);
    const historyRows = get(derived);
    return [SourceKind.BLOCKCHAIN, SourceKind.EXCHANGE, SourceKind.BANK, SourceKind.MANUAL]
      .filter(kind => [...queriedRows, ...historyRows].some(contribution => contribution.kind === kind))
      .map((kind): SourceDifference => {
        if (DERIVED_KINDS.includes(kind))
          return { basis: 'derived', delta: totalOf(historyRows, kind).minus(totalOf(queriedRows, kind)), kind };
        if (kind === SourceKind.MANUAL)
          return { basis: 'excluded', delta: totalOf(queriedRows, kind).negated(), kind };
        return { basis: 'queried', delta: Zero, kind };
      });
  });
}

/** Identifies a contribution's place and kind, so the same holding can be matched across views. */
function placeKey(contribution: SourceContribution): string {
  return `${contribution.kind}:${contribution.kind === SourceKind.BLOCKCHAIN ? contribution.chain : contribution.location}`;
}

/**
 * The holdings only `other` has, as excluded placeholders worth nothing.
 *
 * @remarks
 * Added to the view on show, they keep every legend row and tile that the other view has, so
 * switching views changes values in place instead of adding or removing rows and tiles. A place the
 * other view holds nothing at gets no placeholder, since that view shows no tile for it either.
 */
function placeholdersFrom(shown: readonly SourceContribution[], other: readonly SourceContribution[]): SourceContribution[] {
  const present = new Set(shown.map(placeKey));
  return other
    .filter(contribution => !contribution.value.isZero() && !present.has(placeKey(contribution)))
    .map((contribution): SourceContribution => ({ ...contribution, excluded: true, loading: false, value: Zero }));
}

/**
 * The dashboard's net worth breakdown in the page's balance view.
 *
 * @remarks
 * In the history view, chains and exchanges come from history buckets, banks stay queried because
 * history has no bank events, and manual balances are left out, as are manual liabilities. Once the
 * history snapshot has loaded, each view also lists, as excluded, whatever only the other view
 * holds, so both views show the same legend rows and tiles. Before history has been processed
 * there is nothing to compare, so the queried breakdown is shown as it is. NFTs count the same in both views.
 */
export function useViewHoldingsContributions(): HoldingsInputs {
  const isHistory = useIsHistoryView();
  const queried = useHoldingsContributions();
  const derived = useDerivedContributions();
  const { getLiabilities } = useHistoryBalances();
  const { manualLiabilities } = storeToRefs(useBalancesStore());
  const { hasData } = storeToRefs(useHistoricalSnapshotStore());

  const historyContributions = computed<SourceContribution[]>(() => [
    ...get(derived),
    ...get(queried.contributions).filter(({ kind }) => kind === SourceKind.BANK),
  ]);

  const contributions = computed<SourceContribution[]>(() => {
    const queriedRows = get(queried.contributions);
    if (!get(hasData))
      return queriedRows;

    const historyRows = get(historyContributions);
    return get(isHistory)
      ? [...historyRows, ...placeholdersFrom(historyRows, queriedRows)]
      : [...queriedRows, ...placeholdersFrom(queriedRows, historyRows)];
  });

  /** Each place weighed by the larger of its two views' values, so both views order tiles alike. */
  const placeRank = computed<ReadonlyMap<string, BigNumber> | undefined>(() => {
    if (!get(hasData))
      return undefined;
    const rank = new Map<string, BigNumber>();
    for (const rows of [get(queried.contributions), get(historyContributions)]) {
      for (const holding of mergeLocations(rows, { locationOfChain: queried.locationOfChain })) {
        const current = rank.get(holding.place.key);
        if (!current || holding.value.gt(current))
          rank.set(holding.place.key, holding.value);
      }
    }
    return rank;
  });

  return {
    contributions,
    liabilities: computed<BigNumber>(() => (get(isHistory)
      ? bigNumberSum(getLiabilities().map(({ value }) => value))
      : get(queried.liabilities))),
    liabilitiesExcluded: computed<boolean>(() => get(isHistory) && get(manualLiabilities).length > 0),
    locationOfChain: queried.locationOfChain,
    nfts: queried.nfts,
    placeRank,
  };
}
