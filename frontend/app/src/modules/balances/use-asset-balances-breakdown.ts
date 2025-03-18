import type { Accounts, AssetBreakdown, Balances } from '@/types/blockchain/accounts';
import type { ExchangeData } from '@/types/exchanges';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { groupAssetBreakdown } from '@/utils/balances';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';

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
}

export function useAssetBalancesBreakdown(): UseAssetBalancesBreakdownReturn {
  const { balances, exchangeBalances, manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { getEvmChainName } = useSupportedChains();
  const { assetAssociationMap } = useAssetInfoRetrieval();

  const getExchangeAssetBreakdown = (
    balances: ExchangeData,
    asset: string,
    assetAssociationMap: Record<string, string>,
  ): AssetBreakdown[] => {
    const breakdown: AssetBreakdown[] = [];
    for (const exchange in balances) {
      const exchangeData = balances[exchange];
      for (const exchangeDataAsset in exchangeData) {
        if ((assetAssociationMap?.[exchangeDataAsset] ?? exchangeDataAsset) !== asset)
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
    assetAssociationMap: Record<string, string>,
  ): AssetBreakdown[] {
    const breakdown: AssetBreakdown[] = [];
    for (const balance of balances) {
      if ((assetAssociationMap?.[balance.asset] ?? balance.asset) !== asset)
        continue;

      breakdown.push({
        address: '',
        amount: balance.amount,
        location: balance.location,
        tags: balance.tags && balance.tags.length > 0 ? balance.tags : undefined,
        usdValue: balance.usdValue,
      });
    }
    return breakdown;
  }

  function getBlockchainAssetBreakdown(
    data: BreakdownData,
    asset: string,
    isLiability: boolean = false,
    associatedIdentifiers: Record<string, string> = {},
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
        return [];

      for (const address in chainBalanceData) {
        if (groupId && address !== groupId)
          continue;

        const balance = chainBalanceData[address];
        const identifiers = associatedIdentifiers[asset] ? [asset, associatedIdentifiers[asset]] : [asset];
        for (const identifier of identifiers) {
          const assetBalance = balance[isLiability ? 'liabilities' : 'assets'][identifier];
          if (!assetBalance)
            continue;

          breakdown.push({
            address,
            location: getEvmChainName(chain) ?? chain,
            ...assetBalance,
            tags: chainAccounts.find(account => getAccountAddress(account) === address && account.chain === chain)
              ?.tags,
          });
        }
      }
    }

    return breakdown;
  }

  const useAssetBreakdown = (
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

    const associatedIdentifiers = get(assetAssociationMap);
    data.push(...getBlockchainAssetBreakdown(
      { accounts: get(accounts), balances: get(balances) },
      asset,
      liabilities,
      associatedIdentifiers,
    ));

    if (!onlyBlockchain) {
      const balances = liabilities ? get(manualLiabilities) : get(manualBalances);
      data.push(...getManualBalancesAssetBreakdown(balances, asset, associatedIdentifiers));
      if (!liabilities) {
        data.push(...getExchangeAssetBreakdown(
          get(exchangeBalances),
          asset,
          associatedIdentifiers,
        ));
      }
    }

    return groupAssetBreakdown(data.filter(item => !!item.amount && !item.amount.isZero()));
  });

  return {
    useAssetBreakdown,
  };
}
