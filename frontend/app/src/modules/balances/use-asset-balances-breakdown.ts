import type { ComputedRef } from 'vue';
import type { Accounts, AssetBreakdown, Balances } from '@/modules/accounts/blockchain-accounts';
import type { ExchangeData } from '@/modules/balances/types/exchanges';
import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { Zero } from '@rotki/common';
import { useResolveAssetIdentifier } from '@/composables/assets/common';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { groupAssetBreakdown } from '@/utils/balances';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { perProtocolBalanceSum } from '@/utils/calculation';

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

interface UseAssetBalancesBreakdownReturn {
  useAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownExtendedFilters) => ComputedRef<AssetBreakdown[]>;
  getAssetBreakdown: (asset: string, liabilities?: boolean, filters?: BreakdownExtendedFilters) => AssetBreakdown[];
}

export function useAssetBalancesBreakdown(): UseAssetBalancesBreakdownReturn {
  const { balances, exchangeBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { getEvmChainName } = useSupportedChains();
  const resolveAssetIdentifier = useResolveAssetIdentifier();

  const getExchangeAssetBreakdown = (
    balances: ExchangeData,
    asset: string,
  ): AssetBreakdown[] => {
    const breakdown: AssetBreakdown[] = [];
    for (const exchange in balances) {
      const exchangeData = balances[exchange];
      for (const exchangeDataAsset in exchangeData) {
        if (resolveAssetIdentifier(exchangeDataAsset) !== asset)
          continue;

        breakdown.push({
          address: '',
          location: exchange,
          tags: undefined,
          ...exchangeData[exchangeDataAsset],
        });
      }
    }
    return breakdown;
  };

  function getManualBalancesAssetBreakdown(
    balances: ManualBalanceWithValue[],
    asset: string,
  ): AssetBreakdown[] {
    const breakdown: AssetBreakdown[] = [];
    for (const balance of balances) {
      if (resolveAssetIdentifier(balance.asset) !== asset)
        continue;

      breakdown.push({
        address: '',
        amount: balance.amount,
        location: balance.location,
        tags: balance.tags && balance.tags.length > 0 ? balance.tags : undefined,
        value: balance.value,
      });
    }
    return breakdown;
  }

  function getBlockchainAssetBreakdown(
    data: BreakdownData,
    asset: string,
    isLiability: boolean = false,
    filters: BreakdownFilters = {},
  ): AssetBreakdown[] {
    const breakdown: AssetBreakdown[] = [];
    const { chains = [], groupId } = filters;
    const { accounts: accountData, balances: balanceData } = data;

    const chainList = chains.length > 0 ? chains : Object.keys(accountData);

    for (const chain of chainList) {
      const chainAccounts = accountData[chain] ?? {};
      const chainBalanceData = balanceData[chain];
      if (!chainBalanceData)
        continue;

      for (const address in chainBalanceData) {
        if (groupId && address !== groupId)
          continue;

        const balance = chainBalanceData[address];
        const resolved = resolveAssetIdentifier(asset);
        const identifiers = resolved !== asset ? [asset, resolved] : [asset];
        for (const identifier of identifiers) {
          const assetBalance = balance[isLiability ? 'liabilities' : 'assets'][identifier];
          if (!assetBalance)
            continue;

          const summedBalance = perProtocolBalanceSum({
            amount: Zero,
            value: Zero,
          }, assetBalance);

          breakdown.push({
            address,
            location: getEvmChainName(chain) ?? chain,
            ...summedBalance,
            tags: chainAccounts.find(account => getAccountAddress(account) === address && account.chain === chain)
              ?.tags,
          });
        }
      }
    }

    return breakdown;
  }

  function getAssetBreakdown(
    asset: string,
    liabilities: boolean = false,
    filters: BreakdownExtendedFilters = {},
  ): AssetBreakdown[] {
    const data: AssetBreakdown[] = [];
    const {
      blockchainOnly = false,
      chains = [],
      groupId,
    } = filters;

    const onlyBlockchain = chains.length > 0 || groupId !== undefined || blockchainOnly;

    data.push(...getBlockchainAssetBreakdown(
      { accounts: get(accounts), balances: get(balances) },
      asset,
      liabilities,
      filters,
    ));

    if (!onlyBlockchain) {
      const balanceData = liabilities ? get(manualLiabilities) : get(manualBalances);
      data.push(...getManualBalancesAssetBreakdown(balanceData, asset));
      if (!liabilities) {
        data.push(...getExchangeAssetBreakdown(
          get(exchangeBalances),
          asset,
        ));
      }
    }

    return groupAssetBreakdown(data.filter(item => !!item.amount && !item.amount.isZero()));
  }

  const useAssetBreakdown = (
    asset: string,
    liabilities: boolean = false,
    filters: BreakdownExtendedFilters = {},
  ): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() => getAssetBreakdown(asset, liabilities, filters));

  return {
    getAssetBreakdown,
    useAssetBreakdown,
  };
}
