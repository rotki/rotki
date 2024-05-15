import { camelCase, isEmpty } from 'lodash-es';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef, objectOmit } from '@vueuse/core';
import { getAccountAddress } from '@/utils/blockchain/accounts';
import type {
  AssetBreakdown,
  BlockchainAccount,
  BlockchainAccountWithBalance,
  ValidatorData,
} from '@/types/blockchain/accounts';
import type { BlockchainTotal } from '@/types/blockchain';
import type { AssetBalances } from '@/types/balances';
import type { BlockchainAssetBalances, BlockchainBalances } from '@/types/blockchain/balances';
import type { AssetPrices } from '@/types/prices';
import type { AssetBalance } from '@rotki/common';

type Accounts = Record<string, BlockchainAccount[]>;

type Totals = Record<string, AssetBalances>;

type Balances = Record<string, BlockchainAssetBalances>;

function aggregateTotals(totals: Totals): AssetBalances {
  const balances: AssetBalances = {};
  for (const value of Object.values(totals)) {
    for (const asset of Object.keys(value)) {
      if (!balances[asset])
        balances[asset] = value[asset];
      else
        balances[asset] = balanceSum(balances[asset], value[asset]);
    }
  }

  return balances;
}

function hasTokens(nativeAsset: string, assetBalances?: AssetBalances): boolean {
  if (!assetBalances || isEmpty(assetBalances))
    return false;

  return !isEmpty(objectOmit(assetBalances, [nativeAsset]));
}

function getAccountBalance(account: BlockchainAccount, chainBalances: BlockchainAssetBalances) {
  const address = getAccountAddress(account);
  const accountBalances = chainBalances?.[address] ?? {};
  const assets = accountBalances?.assets;
  const nativeAsset = account.nativeAsset;
  const balance = assets
    ? {
        amount: assets[nativeAsset]?.amount ?? Zero,
        usdValue: assetSum(accountBalances.assets),
      }
    : {
        amount: Zero,
        usdValue: Zero,
      };

  const expandable = hasTokens(nativeAsset, accountBalances.assets)
    || hasTokens(nativeAsset, accountBalances.liabilities);
  return { balance, expandable };
}

function createAccountWithBalance(
  account: BlockchainAccount,
  chainBalances: BlockchainAssetBalances,
) {
  const { balance, expandable } = getAccountBalance(account, chainBalances);
  const address = getAccountAddress(account);

  return {
    groupId: address,
    ...account,
    ...balance,
    expandable,
  } satisfies BlockchainAccountWithBalance;
}

export const useBlockchainStore = defineStore('blockchain', () => {
  const accounts = ref<Accounts>({});
  const balances = ref<Balances>({});
  const totals = ref<Totals>({});
  const liabilities = ref<Totals>({});
  const stakingValidatorsLimits = ref<{
    limit: number;
    total: number;
  }>();

  const addresses = computed<Record<string, string[]>>(() => {
    const accountData = get(accounts);
    if (!accountData)
      return {};

    return Object.fromEntries(
      Object.entries(accountData).map(([chain, accounts]) => [
        chain,
        accounts.filter(hasAccountAddress).map(account => getAccountAddress(account)),
      ]),
    );
  });

  const aggregatedTotals = computed<AssetBalances>(() => aggregateTotals(get(totals)));

  const aggregatedLiabilities = computed<AssetBalances>(() => aggregateTotals(get(liabilities)));

  const blockchainAccounts = computed<Record<string, BlockchainAccountWithBalance[]>>(() => {
    const accountData = get(accounts);
    const balanceData = get(balances);

    const entries = Object.entries(accountData).map(([chain, accounts]) => {
      const chainBalances = balanceData[chain] ?? {};
      return [
        chain,
        accounts.map(account => createAccountWithBalance(account, chainBalances)),
      ];
    });

    return Object.fromEntries(entries);
  });

  const ethStakingValidators = computed<BlockchainAccountWithBalance<ValidatorData>[]>(() => {
    const validatorAccounts = get(blockchainAccounts)[Blockchain.ETH2] ?? [];
    return validatorAccounts.filter(isAccountWithBalanceValidator);
  });

  const blockchainTotals = computed<BlockchainTotal[]>(() =>
    Object.entries(get(blockchainAccounts))
      .map(([chain, accounts]) => ({
        chain,
        children: [],
        usdValue: sum(accounts),
        loading: false,
      }))
      .filter(item => item.usdValue.gt(0))
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue)),
  );

  const blockchainAccountList = computed<BlockchainAccountWithBalance[]>(
    () => Object.values(get(blockchainAccounts))
      .reduce((previousValue, currentValue) => [...previousValue, ...currentValue], []),
  );

  const removeTag = (tag: string) => {
    const copy = { ...get(accounts) };
    for (const chain in copy) {
      const accountData = copy[chain];
      copy[chain] = removeTags(accountData, tag);
    }

    set(accounts, copy);
  };

  const updateAccounts = (chain: string, data: BlockchainAccount[]) => {
    set(accounts, { ...get(accounts), [chain]: data });
  };

  const updateBalances = (
    chain: string,
    { perAccount, totals: updatedTotals }: BlockchainBalances,
  ) => {
    set(balances, {
      ...get(balances),
      [chain]: perAccount[camelCase(chain)] ?? {},
    });

    set(totals, {
      ...get(totals),
      [chain]: removeZeroAssets(updatedTotals.assets),
    });

    set(liabilities, {
      ...get(liabilities),
      [chain]: removeZeroAssets(updatedTotals.liabilities),
    });
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>) => {
    set(totals, updateTotalsPrices(totals, prices));
    set(liabilities, updateTotalsPrices(liabilities, prices));
    set(balances, updateBlockchainAssetBalances(balances, prices));
  };

  const getAccounts = (chain: string): BlockchainAccount[] => get(accounts)[chain] ?? [];

  const getAddressBalances = (chain: string, address: string) => get(balances)[chain]?.[address] ?? { assets: {}, liabilities: {} };

  const getAccountByAddress = (address: string, chain?: string): BlockchainAccount | undefined => {
    const knownAccounts = get(accounts);
    if (chain && knownAccounts[chain])
      return knownAccounts[chain].find(account => getAccountAddress(account) === address);

    return Object.values(knownAccounts)
      .flatMap(x => x)
      .find(account => getAccountAddress(account) === address);
  };

  const getBlockchainAccounts = (chain: string): BlockchainAccountWithBalance[] => get(blockchainAccounts)[chain] ?? [];

  const getAddresses = (chain: string): string[] => get(addresses)[chain] ?? [];

  const getBreakdown = (asset: string, chain?: string): AssetBreakdown[] => {
    const breakdown: AssetBreakdown[] = [];
    const balanceData = get(balances);
    const accountData = get(accounts);

    const chains = chain ? [chain] : Object.keys(accountData);

    for (const chain of chains) {
      const chainAccounts = accountData[chain] ?? {};
      const chainBalanceData = balanceData[chain];
      if (!chainBalanceData)
        return [];

      for (const address in chainBalanceData) {
        const balance = chainBalanceData[address];
        const assetBalance = balance.assets[asset];
        if (!assetBalance)
          continue;

        breakdown.push({
          address,
          location: chain,
          ...assetBalance,
          tags: chainAccounts.find(account => getAccountAddress(account) === address && account.chain === chain)?.tags,
        });
      }
    }

    return breakdown;
  };

  const getAccountDetails = (chain: string, address: string): {
    assets: AssetBalance[];
    liabilities: AssetBalance[];
  } => {
    const chainAssets = get(balances)[chain] ?? {};
    const addressAssets = chainAssets[address];

    if (addressAssets) {
      const { assets, liabilities } = addressAssets;
      return {
        assets: Object.entries(assets).map(([asset, balance]) => ({ asset, ...balance })),
        liabilities: Object.entries(liabilities).map(([asset, balance]) => ({ asset, ...balance })),
      };
    }

    return {
      assets: [],
      liabilities: [],
    };
  };

  return {
    accounts,
    addresses,
    balances,
    totals,
    liabilities,
    stakingValidatorsLimits,
    ethStakingValidators,
    aggregatedTotals,
    aggregatedLiabilities,
    blockchainAccounts,
    blockchainAccountList,
    blockchainTotals,
    getAccounts,
    getBlockchainAccounts,
    getAccountByAddress,
    getAccountDetails,
    getAddresses,
    getAddressBalances,
    getBreakdown,
    updateAccounts,
    updateBalances,
    updatePrices,
    removeTag,
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useBlockchainStore, import.meta.hot),
  );
}
