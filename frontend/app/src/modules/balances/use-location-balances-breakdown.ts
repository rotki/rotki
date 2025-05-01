import type { AssetBalances } from '@/types/balances';
import type { Balances } from '@/types/blockchain/accounts';
import type { Exchange, ExchangeData, ExchangeInfo } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useSessionSettingsStore } from '@/store/settings/session';
import { appendAssetBalance, mergeAssetBalances } from '@/utils/balances';
import { aggregateTotals } from '@/utils/blockchain/accounts';
import { bigNumberSum } from '@/utils/calculation';

interface UseLocationBalancesBreakdownReturn {
  useLocationBreakdown: (identifier: MaybeRef<string>) => ComputedRef<AssetBalanceWithPrice[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
}

export function useLocationBalancesBreakdown(): UseLocationBalancesBreakdownReturn {
  const { manualBalanceByLocation } = useManualBalanceData();
  const { balances: blockchainBalances, exchangeBalances, manualBalances } = storeToRefs(useBalancesStore());
  const { assetPrice, toSelectedCurrency } = usePriceUtils();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();
  const { assetAssociationMap } = useAssetInfoRetrieval();
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { exchanges } = useExchangeData();

  const getExchangesLocationBreakdown = (
    connectedExchanges: Exchange[],
    exchangeData: ExchangeData,
    location: string,
    assetAssociationMap: Record<string, string>,
  ): AssetBalances => {
    const assets: AssetBalances = {};
    const connectedExchange = connectedExchanges.find(exchange => exchange.location === location);

    if (!connectedExchange) {
      return {};
    }

    const connectedLocation = connectedExchange.location;
    const balances = exchangeData[connectedLocation];

    for (const asset in balances) {
      if (isAssetIgnored(asset)) {
        continue;
      }
      const balance = {
        ...balances[asset],
        asset,
      };
      appendAssetBalance(balance, assets, assetAssociationMap);
    }

    return assets;
  };

  const getExchangeByLocationBalances = (
    exchanges: ExchangeInfo[],
    convert: (bn: BigNumber) => BigNumber,
  ): Record<string, BigNumber> => {
    const balances: Record<string, BigNumber> = {};
    for (const { location, total } of exchanges) {
      const balance = balances[location];
      const value = convert(total);
      balances[location] = !balance ? value : value.plus(balance);
    }
    return balances;
  };

  const getManualLocationBreakdown = (
    balances: ManualBalanceWithValue[],
    location: string,
    assetAssociationMap: Record<string, string>,
  ): AssetBalances => {
    const assets: AssetBalances = {};
    for (const balance of balances) {
      if (balance.location !== location)
        continue;

      appendAssetBalance(balance, assets, assetAssociationMap);
    }
    return assets;
  };

  const getBlockchainLocationBreakdown = (
    balances: Balances,
    assetAssociationMap: Record<string, string>,
  ): AssetBalances => aggregateTotals(balances, 'assets', {
    assetAssociationMap,
    skipIdentifier: asset => isAssetIgnored(asset),
  });

  const useLocationBreakdown = (
    location: MaybeRef<string>,
  ): ComputedRef<AssetBalanceWithPrice[]> => computed<AssetBalanceWithPrice[]>(() => {
    const selectedLocation = get(location);
    const associationMap = get(assetAssociationMap);
    const manualLocationBreakdown = getManualLocationBreakdown(
      get(manualBalances),
      selectedLocation,
      associationMap,
    );
    const exchangesLocationBreakdown = getExchangesLocationBreakdown(
      get(connectedExchanges),
      get(exchangeBalances),
      selectedLocation,
      associationMap,
    );
    let balances = mergeAssetBalances(manualLocationBreakdown, exchangesLocationBreakdown);

    if (selectedLocation === TRADE_LOCATION_BLOCKCHAIN)
      balances = mergeAssetBalances(balances, getBlockchainLocationBreakdown(get(blockchainBalances), associationMap));

    return toSortedAssetBalanceWithPrice(balances, asset => isAssetIgnored(asset), assetPrice, true);
  });

  const balancesByLocation = computed<Record<string, BigNumber>>(() => {
    const blockchainAssets = getBlockchainLocationBreakdown(get(blockchainBalances), get(assetAssociationMap));
    const blockchainTotal = bigNumberSum(Object.values(blockchainAssets).map(asset => asset.usdValue));
    const map: Record<string, BigNumber> = {
      [TRADE_LOCATION_BLOCKCHAIN]: get(toSelectedCurrency(blockchainTotal)),
    };

    const exchange = getExchangeByLocationBalances(get(exchanges), bn => get(toSelectedCurrency(bn)));
    for (const location in exchange) {
      const total = map[location];
      const usdValue = exchange[location];
      map[location] = total ? total.plus(usdValue) : usdValue;
    }

    const manual = get(manualBalanceByLocation);
    for (const { location, usdValue } of manual) {
      const total = map[location];
      map[location] = total ? total.plus(usdValue) : usdValue;
    }

    return map;
  });

  return {
    balancesByLocation,
    useLocationBreakdown,
  };
}
