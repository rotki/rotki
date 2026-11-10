import type { AssetPriceInfo } from '@/modules/assets/prices/price-types';
import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import { type AssetBalanceWithPrice, type AssetBalanceWithPriceAndChains, type BigNumber, type ExclusionSource, Zero } from '@rotki/common';
import { computed, type ComputedRef, type MaybeRefOrGetter } from 'vue';
import { groupAddresses } from '@/modules/accounts/core/account-groups';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { heldAssets } from '@/modules/balances/aggregation/core/held-assets';
import { type BalanceInputs, locationSources } from '@/modules/balances/aggregation/core/location-sources';
import { blockchainValue, locationMapTotals, totalsByChainLocation, totalsByLocation } from '@/modules/balances/aggregation/core/location-totals';
import { fromBlockchain, fromExchanges, fromManual } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalBalanceSource } from '@/modules/balances/use-historical-balance-source';
import { bankLocationBalances } from '@/modules/banks/bank-balances';
import { useLocations } from '@/modules/core/common/use-locations';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface UseAggregatedBalancesReturn {
  useBalances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getBalances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => AssetBalanceWithPriceAndChains[];
  useLiabilities: (hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getLiabilities: (hideIgnored?: boolean) => AssetBalanceWithPriceAndChains[];
  getAssetPriceInfo: (identifier: string, groupMultiChain?: boolean) => AssetPriceInfo;
  getQueriedAssetPriceInfo: (identifier: string, groupMultiChain?: boolean) => AssetPriceInfo;
  getHistoryAssetPriceInfo: (identifier: string, groupMultiChain?: boolean) => AssetPriceInfo;
  useAssetPriceInfo: (identifier: MaybeRefOrGetter<string>, groupCollection?: MaybeRefOrGetter<boolean>) => ComputedRef<AssetPriceInfo>;
  assets: ComputedRef<string[]>;
  useBlockchainBalances: (chains: MaybeRefOrGetter<string[]>, groupId?: MaybeRefOrGetter<string>, key?: keyof EthBalance) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getExchangeBalances: (exchange?: string) => AssetBalanceWithPriceAndChains[];
  getExchangeAccountBalances: (exchange: string, identifier: string) => AssetBalanceWithPriceAndChains[];
  useExchangeBalances: (exchange?: MaybeRefOrGetter<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  useLocationBreakdown: (location: MaybeRefOrGetter<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
  balancesByChainLocation: ComputedRef<Record<string, BigNumber>>;
}

const EXCLUDABLE_SOURCES = ['blockchain', 'exchange', 'manual'] as const satisfies readonly ExclusionSource[];

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { balances: allBlockchainBalances, bankBalances, exchangeAccountBalances, exchangeBalances, manualBalances, manualLiabilities, visibleBalances: blockchainBalances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { manualBalanceByLocation } = useManualBalanceData();
  const { tradeLocations } = useLocations();
  const { matchChain } = useSupportedChains();

  const context = useAggregationContext();
  const { isAssetIgnored } = context;
  const {
    isHistoryMode,
    source: historicalAssets,
    sourceForChains: historicalForChains,
    unfilteredSource: historicalUnfiltered,
  } = useHistoricalBalanceSource(context);

  const blockchainAssets = computed<AssetBalanceEntries>(() => fromBlockchain(get(blockchainBalances)));
  const blockchainLiabilities = computed<AssetBalanceEntries>(() => fromBlockchain(get(blockchainBalances), { key: 'liabilities' }));
  /**
   * Every non-chain location's balances: each exchange, and every bank connection as `banks`.
   *
   * @remarks
   * Banks are kept apart from the exchanges in the store, and join them here only as one more
   * location. They count with the `exchange` source, so excluding exchanges leaves them out too,
   * as the premium `balances` contract expects until a bank exclusion source exists.
   */
  const locationBalances = computed<ExchangeData>(() => ({ ...get(exchangeBalances), ...bankLocationBalances(get(bankBalances)) }));
  const exchangeAssets = computed<AssetBalanceEntries>(() => fromExchanges(get(locationBalances)));
  const manualAssets = computed<AssetBalanceEntries>(() => fromManual(get(manualBalances)));
  const manualLiabilityEntries = computed<AssetBalanceEntries>(() => fromManual(get(manualLiabilities)));

  const assetSources: Record<ExclusionSource, ComputedRef<AssetBalanceEntries>> = {
    blockchain: blockchainAssets,
    exchange: exchangeAssets,
    manual: manualAssets,
  };

  function queriedBalances(hideIgnored = true, groupCollections = true, exclude: ExclusionSource[] = []): AssetBalanceWithPriceAndChains[] {
    const sources = EXCLUDABLE_SOURCES
      .filter(source => !exclude.includes(source))
      .map(source => get(assetSources[source]));
    return summarizeBalances(sources, context, { groupCollections, hideIgnored });
  }

  function getBalances(hideIgnored = true, groupCollections = true, exclude: ExclusionSource[] = []): AssetBalanceWithPriceAndChains[] {
    if (get(isHistoryMode))
      return summarizeBalances([get(historicalAssets)], context, { groupCollections, hideIgnored });

    return queriedBalances(hideIgnored, groupCollections, exclude);
  }

  /** History-derived balances have no separate negative liability buckets. */
  function getLiabilities(hideIgnored = true): AssetBalanceWithPriceAndChains[] {
    if (get(isHistoryMode))
      return [];

    return summarizeBalances([get(blockchainLiabilities), get(manualLiabilityEntries)], context, { hideIgnored });
  }

  function priceInfoOf(rows: AssetBalanceWithPriceAndChains[], identifier: string): AssetPriceInfo {
    const assetValue = rows.find((value: AssetBalanceWithPrice) => value.asset === identifier);
    return {
      amount: assetValue?.amount ?? Zero,
      price: assetValue?.price ?? Zero,
      value: assetValue?.value ?? Zero,
    };
  }

  function getAssetPriceInfo(identifier: string, groupMultiChain = false): AssetPriceInfo {
    return priceInfoOf(getBalances(true, groupMultiChain), identifier);
  }

  /** The queried amount regardless of the active display mode, for side-by-side comparison. */
  function getQueriedAssetPriceInfo(identifier: string, groupMultiChain = false): AssetPriceInfo {
    return priceInfoOf(queriedBalances(true, groupMultiChain), identifier);
  }

  /** The history-derived amount regardless of the active display mode, for side-by-side comparison. */
  function getHistoryAssetPriceInfo(identifier: string, groupMultiChain = false): AssetPriceInfo {
    return priceInfoOf(summarizeBalances([get(historicalAssets)], context, { groupCollections: groupMultiChain, hideIgnored: true }), identifier);
  }

  const useBalances = (
    hideIgnored = true,
    groupCollections = true,
    exclude: ExclusionSource[] = [],
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => getBalances(hideIgnored, groupCollections, exclude));

  const useLiabilities = (hideIgnored = true): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => getLiabilities(hideIgnored));

  const useAssetPriceInfo = (
    identifier: MaybeRefOrGetter<string>,
    groupMultiChain: MaybeRefOrGetter<boolean> = false,
  ): ComputedRef<AssetPriceInfo> => computed<AssetPriceInfo>(() => getAssetPriceInfo(toValue(identifier), toValue(groupMultiChain)));

  const useBlockchainBalances = (
    chains: MaybeRefOrGetter<string[]> = [],
    groupId?: MaybeRefOrGetter<string>,
    key: keyof EthBalance = 'assets',
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => {
    if (get(isHistoryMode)) {
      return summarizeBalances([historicalForChains(toValue(chains))], context);
    }

    const group = groupId ? toValue(groupId) : undefined;
    const source = fromBlockchain(get(blockchainBalances), {
      addresses: group ? groupAddresses(get(accounts), group) : undefined,
      chains: toValue(chains),
      key,
    });
    return summarizeBalances([source], context);
  });

  /** One exchange's balances, or every exchange's together. */
  function getExchangeBalances(exchange?: string): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([fromExchanges(get(exchangeBalances), exchange)], context);
  }

  /**
   * The balances of one connection of an exchange, by its stable identifier.
   *
   * @remarks
   * The backend reports these without the hide-small-balances threshold it applies to the totals.
   */
  function getExchangeAccountBalances(exchange: string, identifier: string): AssetBalanceWithPriceAndChains[] {
    const account = get(exchangeAccountBalances)[exchange]?.[identifier] ?? {};
    return summarizeBalances([fromExchanges({ [exchange]: account }, exchange)], context);
  }

  const useLocationBreakdown = (location: MaybeRefOrGetter<string>): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => {
      const selected = toValue(location);
      const inputs: BalanceInputs = {
        blockchain: get(blockchainBalances),
        exchanges: get(locationBalances),
        manual: get(manualBalances),
      };
      return summarizeBalances(locationSources(selected, inputs, matchChain(selected)), context);
    });

  const useExchangeBalances = (
    exchange?: MaybeRefOrGetter<string>,
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() =>
    getExchangeBalances(exchange ? toValue(exchange) : undefined),
  );

  /** Read from the unfiltered balances, since an asset hidden for lacking a price still needs one.
   * History-held assets join the union so switching to `history` mode prices an asset whose current
   * queried balance is zero. */
  const assets = computed<string[]>(() => heldAssets([
    fromBlockchain(get(allBlockchainBalances)),
    fromBlockchain(get(allBlockchainBalances), { key: 'liabilities' }),
    get(exchangeAssets),
    get(manualAssets),
    get(manualLiabilityEntries),
    get(historicalUnfiltered),
  ]));

  const balancesByLocation = computed<Record<string, BigNumber>>(() => totalsByLocation(
    blockchainValue(get(blockchainBalances), isAssetIgnored),
    locationMapTotals(get(locationBalances), isAssetIgnored),
    get(manualBalanceByLocation),
  ));

  /**
   * On-chain totals per chain, keyed by trade-location identifier such as `ethereum`.
   *
   * @remarks
   * What makes a chain discoverable in global search. Kept apart from {@link balancesByLocation} so
   * that its umbrella `blockchain` aggregate stays authoritative for the premium consumers that
   * iterate that map.
   */
  const balancesByChainLocation = computed<Record<string, BigNumber>>(() => totalsByChainLocation(
    get(blockchainBalances),
    get(tradeLocations).map(location => location.identifier),
    matchChain,
    isAssetIgnored,
  ));

  return {
    assets,
    balancesByChainLocation,
    balancesByLocation,
    getAssetPriceInfo,
    getBalances,
    getExchangeAccountBalances,
    getExchangeBalances,
    getLiabilities,
    getHistoryAssetPriceInfo,
    getQueriedAssetPriceInfo,
    useAssetPriceInfo,
    useBalances,
    useLiabilities,
    useBlockchainBalances,
    useExchangeBalances,
    useLocationBreakdown,
  };
}
