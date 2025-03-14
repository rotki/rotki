import type { AssetBalances } from '@/types/balances';
import type { Accounts, AssetBreakdown, Balances } from '@/types/blockchain/accounts';
import type { Exchange, ExchangeData, ExchangeInfo } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useBalanceSorting } from '@/composables/balances/sorting';
import { useBlockchainAggregatedBalances } from '@/composables/blockchain/balances/aggregated';
import { TRADE_LOCATION_BLOCKCHAIN } from '@/data/defaults';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useBlockchainStore } from '@/store/blockchain';
import { useSessionSettingsStore } from '@/store/settings/session';
import { appendAssetBalance, groupAssetBreakdown, mergeAssetBalances } from '@/utils/balances';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

interface UseBalancesBreakdownReturn {
  assetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownExtendedFilters) => ComputedRef<AssetBreakdown[]>;
  locationBreakdown: (identifier: MaybeRef<string>) => ComputedRef<AssetBalanceWithPrice[]>;
  balancesByLocation: ComputedRef<Record<string, BigNumber>>;
}

interface BreakdownFilters {
  chains?: string[];
  groupId?: string;
}

interface BreakdownExtendedFilters extends BreakdownFilters {
  blockchainOnly?: boolean;
}

interface BreakdownData {
  accounts: Accounts;
  balances: Balances;
}

export function useBalancesBreakdown(): UseBalancesBreakdownReturn {
  const { manualBalanceByLocation } = useManualBalanceData();
  const { manualBalances, manualLiabilities } = storeToRefs(useManualBalancesStore());
  const { exchangeBalances } = storeToRefs(useExchangeBalancesStore());
  const { accounts, balances } = useBlockchainStore();
  const { blockchainTotal, locationBreakdown: blockchainLocationBreakdown } = useBlockchainAggregatedBalances();
  const { assetPrice, toSelectedCurrency } = useBalancePricesStore();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();
  const { getAssetAssociationIdentifiers, getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { exchanges, getBalances: getExchangeBalances } = useExchangeData();

  const getExchangesLocationBreakdown = (connected: Exchange[], id: string): AssetBalances => {
    const assets: AssetBalances = {};
    const exchange = connected.find(({ location }) => id === location);

    if (exchange) {
      const balances = get(getExchangeBalances(exchange.location));
      for (const balance of balances) appendAssetBalance(balance, assets, getAssociatedAssetIdentifier);
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

  const getExchangeBreakdown = (balances: ExchangeData, asset: string): AssetBreakdown[] => {
    const breakdown: AssetBreakdown[] = [];
    for (const exchange in balances) {
      const exchangeData = balances[exchange];
      for (const exchangeDataAsset in exchangeData) {
        const associatedAsset = get(getAssociatedAssetIdentifier(exchangeDataAsset));
        if (associatedAsset !== asset)
          continue;

        breakdown.push({
          address: '',
          location: exchange,
          tags: [],
          ...exchangeData[exchangeDataAsset],
        });
      }
    }
    return breakdown;
  };

  const getManualLocationBreakdown = (balances: ManualBalanceWithValue[], id: string): AssetBalances => {
    const assets: AssetBalances = {};
    for (const balance of balances) {
      if (balance.location !== id)
        continue;

      appendAssetBalance(balance, assets, getAssociatedAssetIdentifier);
    }
    return assets;
  };

  function calculateManualBreakdown(balances: ManualBalanceWithValue[], asset: string): AssetBreakdown[] {
    const breakdown: AssetBreakdown[] = [];
    for (const balance of balances) {
      const associatedAsset = get(getAssociatedAssetIdentifier(balance.asset));
      if (associatedAsset !== asset)
        continue;

      breakdown.push({
        address: '',
        amount: balance.amount,
        location: balance.location,
        tags: balance.tags ?? undefined,
        usdValue: balance.usdValue,
      });
    }
    return breakdown;
  }

  function calculateBlockchainBreakdown(
    data: BreakdownData,
    asset: string,
    isLiability: boolean = false,
    filters: BreakdownFilters = {},
  ): AssetBreakdown[] {
    const breakdown: AssetBreakdown[] = [];
    const { chains = [], groupId = [] } = filters;
    const { accounts: accountData, balances: balanceData } = data;

    const chainList = chains.length > 0 ? chains : Object.keys(accountData);

    for (const chain of chainList) {
      const chainAccounts = accountData[chain] ?? {};
      const chainBalanceData = balanceData[chain];
      if (!chainBalanceData)
        return [];

      for (const address in chainBalanceData) {
        if (groupId && address !== groupId)
          continue;

        const balance = chainBalanceData[address];
        const assetAssociations = getAssetAssociationIdentifiers(asset);
        assetAssociations.forEach((asset) => {
          const assetBalance = balance[isLiability ? 'liabilities' : 'assets'][asset];
          if (!assetBalance)
            return;

          breakdown.push({
            address,
            location: chain,
            ...assetBalance,
            tags: chainAccounts.find(account => getAccountAddress(account) === address && account.chain === chain)
              ?.tags,
          });
        });
      }
    }

    return breakdown;
  }

  const assetBreakdown = (
    asset: string,
    liabilities: boolean = false,
    filters: BreakdownExtendedFilters = {},
  ): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() => {
    const data: AssetBreakdown[] = [];
    const {
      blockchainOnly = false,
      chains = [],
      groupId,
    } = filters;

    const onlyBlockchain = chains.length > 0 || groupId !== undefined || blockchainOnly;

    data.push(...calculateBlockchainBreakdown(
      { accounts: get(accounts), balances: get(balances) },
      asset,
      liabilities,
    ));

    if (!onlyBlockchain) {
      const balances = liabilities ? get(manualLiabilities) : get(manualBalances);
      data.push(...calculateManualBreakdown(balances, asset));
      if (!liabilities) {
        data.push(...getExchangeBreakdown(get(exchangeBalances), asset));
      }
    }

    return groupAssetBreakdown(data.filter(item => !!item.amount && !item.amount.isZero()));
  });

  const locationBreakdown = (identifier: MaybeRef<string>): ComputedRef<AssetBalanceWithPrice[]> =>
    computed<AssetBalanceWithPrice[]>(() => {
      const id = get(identifier);
      let balances = mergeAssetBalances(
        getManualLocationBreakdown(get(manualBalances), id),
        getExchangesLocationBreakdown(get(connectedExchanges), id),
      );

      if (id === TRADE_LOCATION_BLOCKCHAIN)
        balances = mergeAssetBalances(balances, get(blockchainLocationBreakdown));

      return toSortedAssetBalanceWithPrice(balances, asset => get(isAssetIgnored(asset)), assetPrice, true);
    });

  const balancesByLocation = computed<Record<string, BigNumber>>(() => {
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
    assetBreakdown,
    balancesByLocation,
    locationBreakdown,
  };
}
