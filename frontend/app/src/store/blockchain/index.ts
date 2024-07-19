import { camelCase, isEmpty } from 'lodash-es';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef, objectOmit, objectPick } from '@vueuse/core';
import {
  aggregateTotals,
  createAccountWithBalance,
  getAccountAddress,
  getAccountBalance,
  getAccountLabel,
  hasTokens,
} from '@/utils/blockchain/accounts';
import type { AssetBalance, Balance, BigNumber } from '@rotki/common';
import type {
  Accounts,
  AssetBreakdown,
  Balances,
  BlockchainAccount,
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
  DeleteBlockchainAccountParams,
  EthereumValidator,
  Totals,
} from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { BlockchainTotal } from '@/types/blockchain';
import type { AssetBalances } from '@/types/balances';
import type { BlockchainBalances } from '@/types/blockchain/balances';
import type { AssetPrices } from '@/types/prices';

export const useBlockchainStore = defineStore('blockchain', () => {
  const accounts = ref<Accounts>({});
  const balances = ref<Balances>({});
  const totals = ref<Totals>({});
  const liabilities = ref<Totals>({});
  const stakingValidatorsLimits = ref<{
    limit: number;
    total: number;
  }>();

  const { addressNameSelector } = useAddressesNamesStore();
  const { getChainType } = useSupportedChains();

  const addresses = computed<Record<string, string[]>>(() => {
    const accountData = get(accounts);
    if (!accountData)
      return {};

    return Object.fromEntries(Object.entries(accountData).map(([chain, accounts]) => [
      chain,
      accounts.filter(hasAccountAddress).map(account => getAccountAddress(account)),
    ]));
  });

  const aggregatedTotals = computed<AssetBalances>(() => aggregateTotals(get(totals)));

  const aggregatedLiabilities = computed<AssetBalances>(() => aggregateTotals(get(liabilities)));

  const groups = computed<BlockchainAccountGroupWithBalance[]>(() => {
    const accountData = objectOmit(get(accounts), [Blockchain.ETH2]);
    const balanceData = objectOmit(get(balances), [Blockchain.ETH2]);

    const nonGroupAccounts = Object.values(accountData).flatMap(accounts => accounts.filter(account => !account.groupId));
    const nonGroupAccountAddresses = nonGroupAccounts.map(account => getAccountAddress(account));
    const groupIdentifiers: string[] = nonGroupAccountAddresses.filter(uniqueStrings);

    const groupHeaders = groupIdentifiers.map((address) => {
      const accountAssets = Object.values(balanceData)
        .filter(data => !isEmpty(data) && !isEmpty(data[address]))
        .map(data => data[address]);
      const usdValue = accountAssets.reduce((previousValue, currentValue) => previousValue.plus(assetSum(currentValue.assets)), Zero);

      const accountsForAddress = Object.values(accountData).flatMap(
        accounts => accounts.filter(account => getAccountAddress(account) === address),
      );

      const tags = accountsForAddress.flatMap(account => account.tags ?? []).filter(uniqueStrings);
      const chains = accountsForAddress.map(account => account.chain);
      const label = accountsForAddress.length === 1 ? getAccountLabel(accountsForAddress[0]) : undefined;

      let amount: BigNumber | undefined;
      let nativeAsset: string | undefined;
      let hasAssets = false;
      if (accountsForAddress.length === 1) {
        const account = accountsForAddress[0];
        const assets = accountAssets?.[0]?.assets ?? {};
        amount = assets[account.nativeAsset]?.amount;
        nativeAsset = account.nativeAsset;
        hasAssets = hasTokens(nativeAsset, assets);
      }

      return {
        type: 'group',
        data: accountsForAddress.length === 1 ? accountsForAddress[0].data : { type: 'address', address },
        category: getChainType(chains[0]),
        usdValue,
        amount,
        nativeAsset,
        label,
        tags: tags.length > 0 ? tags : undefined,
        chains,
        expansion: chains.length > 1 ? 'accounts' : (hasAssets ? 'assets' : undefined),
      } satisfies BlockchainAccountGroupWithBalance;
    });

    const preGrouped = Object.values(accountData)
      .flatMap(accounts => accounts.filter(account => account.groupHeader))
      .map((account) => {
        const balance: Balance = { amount: Zero, usdValue: Zero };
        const chainBalances = balanceData[account.chain];
        const accounts = accountData[account.chain];
        const groupAccounts = accounts.filter(acc => !acc.groupHeader && acc.groupId === account.groupId);
        for (const subAccount of groupAccounts) {
          const { balance: subBalance } = getAccountBalance(subAccount, chainBalances);
          if (account.nativeAsset === subAccount.nativeAsset)
            balance.amount = balance.amount.plus(subBalance.amount);

          balance.usdValue = balance.usdValue.plus(subBalance.usdValue);
        }
        return {
          ...objectOmit(account, ['chain', 'groupId', 'groupHeader']),
          ...balance,
          type: 'group',
          chains: [account.chain],
          category: getChainType(account.chain),
          expansion: groupAccounts.length > 0 ? 'accounts' : undefined,
        } satisfies BlockchainAccountGroupWithBalance;
      });
    return [...groupHeaders, ...preGrouped];
  });

  const blockchainAccounts = computed<Record<string, BlockchainAccountWithBalance[]>>(() => {
    const accountData = get(accounts);
    const balanceData = get(balances);

    const entries = Object.entries(accountData).map(([chain, accounts]) => {
      const chainBalances = balanceData[chain] ?? {};
      return [chain, accounts.filter(account => !account.groupHeader).map(account => createAccountWithBalance(account, chainBalances))];
    });

    return Object.fromEntries(entries);
  });

  const ethStakingValidators = computed<EthereumValidator[]>(() => {
    const validatorAccounts = get(blockchainAccounts)[Blockchain.ETH2] ?? [];
    return validatorAccounts.filter(isAccountWithBalanceValidator).map(validator => ({
      ...objectPick(validator, ['usdValue', 'amount']),
      ...validator.data,
    }));
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

  const blockchainAccountList = computed<BlockchainAccountWithBalance[]>(() =>
    Object.values(get(blockchainAccounts)).reduce(
      (previousValue, currentValue) => [...previousValue, ...currentValue],
      [],
    ),
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

  const removeAccounts = ({ accounts: addresses, chain }: DeleteBlockchainAccountParams): void => {
    const knownAccounts = { ...get(accounts) };
    const chainAccounts = knownAccounts[chain];
    if (chainAccounts) {
      knownAccounts[chain] = chainAccounts.filter(account => !addresses.includes(getAccountAddress(account)));
      set(accounts, knownAccounts);
    }

    const knownBalances = { ...get(balances) };
    const chainBalances = knownBalances[chain];

    if (chainBalances) {
      addresses.forEach((address) => {
        if (chainBalances[address])
          delete chainBalances[address];
      });
      knownBalances[chain] = chainBalances;
      set(balances, knownBalances);
    }
  };

  const updateBalances = (chain: string, { perAccount, totals: updatedTotals }: BlockchainBalances) => {
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

  const getAddressBalances = (chain: string, address: string) =>
    get(balances)[chain]?.[address] ?? { assets: {}, liabilities: {} };

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
          tags: chainAccounts.find(account => getAccountAddress(account) === address && account.chain === chain)
            ?.tags,
        });
      }
    }

    return breakdown;
  };

  const getAccountDetails = (
    chain: string,
    address: string,
  ): {
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

  const fetchAccounts = async (
    payload: MaybeRef<BlockchainAccountRequestPayload>,
  ): Promise<Collection<BlockchainAccountGroupWithBalance>> => await new Promise((resolve) => {
    resolve(sortAndFilterAccounts(
      get(groups),
      get(payload),
      {
        getAccounts(groupId: string) {
          return get(blockchainAccountList).filter(account => account.groupId === groupId);
        },
        getLabel(address, chain) {
          return get(addressNameSelector(address, chain));
        },
      },
    ),
    );
  });

  const fetchGroupAccounts = async (
    payload: MaybeRef<BlockchainAccountGroupRequestPayload>,
  ): Promise<Collection<BlockchainAccountWithBalance>> => await new Promise((resolve) => {
    const params = get(payload);
    const newVar = get(blockchainAccountList).filter(account => account.groupId === params.groupId);
    resolve(sortAndFilterAccounts(newVar, params, {
      getLabel(address, chain) {
        return get(addressNameSelector(address, chain));
      },
    }));
  });

  return {
    accounts,
    addresses,
    balances,
    totals,
    liabilities,
    groups,
    stakingValidatorsLimits,
    ethStakingValidators,
    aggregatedTotals,
    aggregatedLiabilities,
    blockchainAccounts,
    blockchainAccountList,
    blockchainTotals,
    fetchAccounts,
    fetchGroupAccounts,
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
    removeAccounts,
    removeTag,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainStore, import.meta.hot));
