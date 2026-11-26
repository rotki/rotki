import type { AssetPriceInfo } from '@/modules/assets/prices/price-types';
import type { AssetBalanceEntries } from '@/modules/balances/aggregation/core/aggregation-types';
import type { EthBalance } from '@/modules/balances/types/blockchain-balances';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import { type AssetBalanceWithPrice, type AssetBalanceWithPriceAndChains, type ExclusionSource, Zero } from '@rotki/common';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { groupAddresses } from '@/modules/accounts/core/account-groups';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { heldAssets } from '@/modules/balances/aggregation/core/held-assets';
import { fromBlockchain, fromExchanges, fromManual } from '@/modules/balances/aggregation/core/sources';
import { summarizeBalances } from '@/modules/balances/aggregation/core/summarize';
import { useAggregationContext } from '@/modules/balances/aggregation/use-aggregation-context';
import { useLocationBalances, type UseLocationBalancesReturn } from '@/modules/balances/aggregation/use-location-balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useHistoricalBalanceSource } from '@/modules/balances/use-historical-balance-source';
import { bankLocationBalances } from '@/modules/banks/bank-balances';

interface UseAggregatedBalancesReturn extends UseLocationBalancesReturn {
  useBalances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getBalances: (hideIgnored?: boolean, groupMultiChain?: boolean, exclude?: ExclusionSource[]) => AssetBalanceWithPriceAndChains[];
  useLiabilities: (hideIgnored?: boolean) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getLiabilities: (hideIgnored?: boolean) => AssetBalanceWithPriceAndChains[];
  getAssetPriceInfo: (identifier: string, groupMultiChain?: boolean) => AssetPriceInfo;
  assets: ComputedRef<string[]>;
  useBlockchainBalances: (chains: MaybeRefOrGetter<string[]>, groupId?: MaybeRefOrGetter<string>, key?: keyof EthBalance) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
  getExchangeBalances: (exchange?: string) => AssetBalanceWithPriceAndChains[];
  getExchangeAccountBalances: (exchange: string, identifier: string) => AssetBalanceWithPriceAndChains[];
  useExchangeBalances: (exchange?: MaybeRefOrGetter<string>) => ComputedRef<AssetBalanceWithPriceAndChains[]>;
}

const EXCLUDABLE_SOURCES = ['blockchain', 'exchange', 'manual'] as const satisfies readonly ExclusionSource[];

export function useAggregatedBalances(): UseAggregatedBalancesReturn {
  const { balances: allBlockchainBalances, bankBalances, exchangeAccountBalances, exchangeBalances, manualBalances, manualLiabilities, visibleBalances: blockchainBalances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());

  const context = useAggregationContext();
  const { unfilteredSource: historicalAssets } = useHistoricalBalanceSource(context);

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

  function getBalances(hideIgnored = true, groupCollections = true, exclude: ExclusionSource[] = []): AssetBalanceWithPriceAndChains[] {
    const sources = EXCLUDABLE_SOURCES
      .filter(source => !exclude.includes(source))
      .map(source => get(assetSources[source]));
    return summarizeBalances(sources, context, { groupCollections, hideIgnored });
  }

  function getLiabilities(hideIgnored = true): AssetBalanceWithPriceAndChains[] {
    return summarizeBalances([get(blockchainLiabilities), get(manualLiabilityEntries)], context, { hideIgnored });
  }

  function getAssetPriceInfo(identifier: string, groupMultiChain = false): AssetPriceInfo {
    const assetValue = getBalances(true, groupMultiChain).find(
      (value: AssetBalanceWithPrice) => value.asset === identifier,
    ) ?? getLiabilities(true).find(
      (value: AssetBalanceWithPrice) => value.asset === identifier,
    );

    return {
      amount: assetValue?.amount ?? Zero,
      price: assetValue?.price ?? Zero,
      value: assetValue?.value ?? Zero,
    };
  }

  const useBalances = (
    hideIgnored = true,
    groupCollections = true,
    exclude: ExclusionSource[] = [],
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => getBalances(hideIgnored, groupCollections, exclude));

  const useLiabilities = (hideIgnored = true): ComputedRef<AssetBalanceWithPriceAndChains[]> =>
    computed<AssetBalanceWithPriceAndChains[]>(() => getLiabilities(hideIgnored));

  const useBlockchainBalances = (
    chains: MaybeRefOrGetter<string[]> = [],
    groupId?: MaybeRefOrGetter<string>,
    key: keyof EthBalance = 'assets',
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() => {
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

  const useExchangeBalances = (
    exchange?: MaybeRefOrGetter<string>,
  ): ComputedRef<AssetBalanceWithPriceAndChains[]> => computed<AssetBalanceWithPriceAndChains[]>(() =>
    getExchangeBalances(exchange ? toValue(exchange) : undefined),
  );

  /**
   * Every asset that needs a price.
   *
   * @remarks
   * Read from the unfiltered balances, since an asset hidden for lacking a price still needs one. The
   * history-derived snapshot joins once loaded, so the history view can price an asset whose queried
   * balance is zero.
   */
  const assets = computed<string[]>(() => heldAssets([
    fromBlockchain(get(allBlockchainBalances)),
    fromBlockchain(get(allBlockchainBalances), { key: 'liabilities' }),
    get(exchangeAssets),
    get(manualAssets),
    get(manualLiabilityEntries),
    get(historicalAssets),
  ]));

  const locationBalanceMembers = useLocationBalances({
    blockchainBalances,
    context,
    locationBalances,
    manualBalances,
  });

  return {
    assets,
    getAssetPriceInfo,
    getBalances,
    getExchangeAccountBalances,
    getExchangeBalances,
    getLiabilities,
    useBalances,
    useLiabilities,
    useBlockchainBalances,
    useExchangeBalances,
    ...locationBalanceMembers,
  };
}
