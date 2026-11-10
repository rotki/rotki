import type { ComputedRef } from 'vue';
import type { Balances } from '@/modules/accounts/blockchain-accounts';
import type { HistoricalBalanceEntry } from '@/modules/history/balances/types';
import { type BigNumber, NoPrice, Zero } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { blockchainValue } from '@/modules/balances/aggregation/core/location-totals';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalanceDisplayModeStore } from '@/modules/balances/use-balance-display-mode-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBankData } from '@/modules/banks/use-bank-data';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
import { TRADE_LOCATION_BANKS, TRADE_LOCATION_BLOCKCHAIN, TRADE_LOCATION_EXTERNAL } from '@/modules/core/common/defaults';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { type SourceContribution, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

export interface HoldingsInputs {
  readonly contributions: ComputedRef<SourceContribution[]>;
  /** NFT value in the main currency, or `undefined` when NFTs do not count toward net worth. */
  readonly nfts: ComputedRef<BigNumber | undefined>;
  readonly liabilities: ComputedRef<BigNumber>;
  readonly locationOfChain: (chain: string) => string | undefined;
}

/**
 * Reads every balance source the dashboard breaks net worth into.
 *
 * @remarks
 * Each value leaves ignored assets out, as net worth does, so the sources minus liabilities add up
 * to the headline.
 */
export function useHoldingsContributions(): HoldingsInputs {
  const { manualBalances, visibleBalances: balances } = storeToRefs(useBalancesStore());
  const { nftValue } = storeToRefs(useStatisticsStore());
  const { isAssetIgnored } = useAssetsStore();
  const { isPricePending } = usePriceUtils();
  const { useLiabilities } = useAggregatedBalances();
  const { exchanges } = useExchangeData();
  const { total: bankTotal } = useBankData();
  const { tradeLocations } = useLocations();
  const { matchChain } = useSupportedChains();
  const nftsInNetValue = useSetting('nftsInNetValue');
  const liabilityBalances = useLiabilities();
  const { isHistoryMode, entries: historicalEntries } = storeToRefs(useBalanceDisplayModeStore());
  const { getAssetPrice } = usePriceUtils();
  const resolveIdentifier = useResolveAssetIdentifier();

  const chainLocations = computed<Map<string, string>>(() => {
    const byChain = new Map<string, string>();
    for (const { identifier } of get(tradeLocations)) {
      const chain = matchChain(identifier);
      if (chain && !byChain.has(chain))
        byChain.set(chain, identifier);
    }
    return byChain;
  });

  function isChainPricePending(accounts: Balances[string]): boolean {
    return Object.values(accounts).some(({ assets }) => Object.keys(assets ?? {})
      .some(asset => !isAssetIgnored(asset) && isPricePending(asset)));
  }

  function chainContribution(chain: string, accounts: Balances[string]): SourceContribution {
    return {
      chain,
      kind: SourceKind.BLOCKCHAIN,
      loading: isChainPricePending(accounts),
      value: blockchainValue({ [chain]: accounts }, isAssetIgnored),
    };
  }

  /** Value of one history bucket at current prices, or zero when the asset has no price. */
  function historyValue(entry: HistoricalBalanceEntry): BigNumber {
    const price = getAssetPrice(resolveIdentifier(entry.asset), NoPrice);
    return price.gt(0) ? entry.amount.multipliedBy(price) : Zero;
  }

  /** The kind of source a history bucket's location belongs to. */
  function historyKind(location: string): { kind: SourceKind; chain?: string } {
    const chain = matchChain(location);
    if (chain !== undefined || location === TRADE_LOCATION_BLOCKCHAIN)
      return { chain: chain ?? TRADE_LOCATION_BLOCKCHAIN, kind: SourceKind.BLOCKCHAIN };
    if (location === TRADE_LOCATION_BANKS)
      return { kind: SourceKind.BANK };
    if (location === TRADE_LOCATION_EXTERNAL)
      return { kind: SourceKind.MANUAL };
    return { kind: SourceKind.EXCHANGE };
  }

  const historicalContributions = computed<SourceContribution[]>(() => {
    const byKey = new Map<string, { value: BigNumber; kind: SourceKind; chain?: string; location?: string }>();
    for (const entry of get(historicalEntries)) {
      if (isAssetIgnored(resolveIdentifier(entry.asset)))
        continue;

      const { chain, kind } = historyKind(entry.location);
      const key = `${kind}:${chain ?? entry.location}`;
      const existing = byKey.get(key);
      const value = historyValue(entry);
      if (existing)
        existing.value = existing.value.plus(value);
      else
        byKey.set(key, { chain, kind, location: entry.location, value });
    }
    return Array.from(byKey.values(), ({ chain, kind, location, value }): SourceContribution => (
      kind === SourceKind.BLOCKCHAIN
        ? { chain: chain ?? TRADE_LOCATION_BLOCKCHAIN, kind, loading: false, value }
        : { kind, loading: false, location: location ?? '', value }
    ));
  });

  const contributions = computed<SourceContribution[]>(() => [
    ...Object.entries(get(balances)).map(([chain, accounts]) => chainContribution(chain, accounts)),
    ...get(exchanges).map(({ location, total }): SourceContribution => ({ kind: SourceKind.EXCHANGE, loading: false, location, value: total })),
    ...(get(bankTotal).isZero()
      ? []
      : [{ kind: SourceKind.BANK, loading: false, location: 'banks', value: get(bankTotal) } satisfies SourceContribution]),
    ...get(manualBalances)
      .filter(({ asset }) => !isAssetIgnored(asset))
      .map(({ location, value }): SourceContribution => ({ kind: SourceKind.MANUAL, loading: false, location, value })),
  ]);

  return {
    contributions: computed<SourceContribution[]>(() => get(get(isHistoryMode) ? historicalContributions : contributions)),
    /** History-derived balances have no separate liabilities. */
    liabilities: computed<BigNumber>(() => get(isHistoryMode)
      ? Zero
      : bigNumberSum(get(liabilityBalances).map(({ value }) => value))),
    locationOfChain: chain => get(chainLocations).get(chain),
    /** NFTs are a queried-only source; leave them out so history-mode gross matches the buckets. */
    nfts: computed<BigNumber | undefined>(() => get(isHistoryMode) || !get(nftsInNetValue) ? undefined : get(nftValue)),
  };
}
