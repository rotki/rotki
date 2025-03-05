import type { BlockchainTotal } from '@/types/blockchain';
import type {
  AccountPayload,
  Accounts,
  Balances,
  BlockchainAccount,
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';
import type { BlockchainBalances, BlockchainTotals } from '@/types/blockchain/balances';
import type { Collection } from '@/types/collection';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { mergeAssociatedAssets, sum } from '@/utils/balances';
import { sortDesc } from '@/utils/bignumbers';
import { getAccountBalance, hasAccountAddress, hasTokens, sortAndFilterAccounts } from '@/utils/blockchain/accounts';
import { createAccountWithBalance } from '@/utils/blockchain/accounts/create-account-with-balance';
import { getAccountAddress, getAccountLabel } from '@/utils/blockchain/accounts/utils';
import { assetSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';
import { updateBlockchainAssetBalances } from '@/utils/prices';
import { removeTags } from '@/utils/tags';
import { type AssetBalance, type Balance, Blockchain, Zero } from '@rotki/common';
import { camelCase, omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

export const useBlockchainStore = defineStore('blockchain', () => {
  const accounts = ref<Accounts>({});
  const balances = ref<Balances>({});

  const { addressNameSelector } = useAddressesNamesStore();
  const { getChainAccountType } = useSupportedChains();

  const addresses = computed<Record<string, string[]>>(() => {
    const accountData = get(accounts);
    if (!accountData)
      return {};

    return Object.fromEntries(Object.entries(accountData).map(([chain, accounts]) => [
      chain,
      accounts.filter(hasAccountAddress).map(account => getAccountAddress(account)),
    ]));
  });

  const groups = computed<BlockchainAccountGroupWithBalance[]>(() => {
    const accountData = omit(get(accounts), [Blockchain.ETH2]);
    const balanceData = omit(get(balances), [Blockchain.ETH2]);

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
      const label = accountsForAddress.length > 0 ? getAccountLabel(accountsForAddress[0]) : undefined;

      let hasAssets = false;
      if (accountsForAddress.length === 1) {
        const account = accountsForAddress[0];
        const assets = accountAssets?.[0]?.assets ?? {};
        hasAssets = hasTokens(account.nativeAsset, assets);
      }

      return {
        category: getChainAccountType(chains[0]),
        chains,
        data: accountsForAddress.length === 1 ? accountsForAddress[0].data : { address, type: 'address' },
        expansion: chains.length > 1 ? 'accounts' : (hasAssets ? 'assets' : undefined),
        label,
        tags: tags.length > 0 ? tags : undefined,
        type: 'group',
        usdValue,
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
          ...omit(account, ['chain', 'groupId', 'groupHeader']),
          ...balance,
          category: getChainAccountType(account.chain),
          chains: [account.chain],
          expansion: groupAccounts.length > 0 ? 'accounts' : undefined,
          type: 'group',
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

  const blockchainTotals = computed<BlockchainTotal[]>(() =>
    Object.entries(get(blockchainAccounts))
      .map(([chain, accounts]) => ({
        chain,
        children: [],
        loading: false,
        usdValue: sum(accounts),
      }))
      .filter(item => item.usdValue.gt(0))
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue)),
  );

  function blockchainAccountList(accounts: Record<string, BlockchainAccountWithBalance[]>): BlockchainAccountWithBalance[] {
    return Object.values(accounts).reduce(
      (previousValue, currentValue) => [...previousValue, ...currentValue],
      [],
    );
  }

  const removeTag = (tag: string): void => {
    const copy = { ...get(accounts) };
    for (const chain in copy) {
      const accountData = copy[chain];
      copy[chain] = removeTags(accountData, tag);
    }

    set(accounts, copy);
  };

  const updateAccounts = (chain: string, data: BlockchainAccount[]): void => {
    set(accounts, { ...get(accounts), [chain]: data });
  };

  const updateAccountData = (data: AccountPayload): void => {
    const allAccounts = { ...get(accounts) };
    const { address, label, tags } = data;

    for (const chain in allAccounts) {
      const accounts: BlockchainAccount[] = [];
      for (const account of allAccounts[chain]) {
        if (getAccountAddress(account) !== address) {
          accounts.push(account);
        }
        else {
          accounts.push({
            ...account,
            label,
            tags: tags || [],
          });
        }
      }
      allAccounts[chain] = accounts;
    }
    set(accounts, allAccounts);
  };

  const removeAccounts = ({ addresses, chains }: { addresses: string[]; chains: string[] }): void => {
    const knownAccounts = { ...get(accounts) };
    const knownBalances = { ...get(balances) };
    const groupAddresses: string[] = [];

    for (const chain of chains) {
      const chainAccounts = knownAccounts[chain];
      if (chainAccounts) {
        const groupIds = chainAccounts
          .filter(account => addresses.includes(getAccountAddress(account)) && account.groupId && account.groupHeader)
          .map(account => account.groupId!);

        const groups = chainAccounts.filter(account => account.groupId && groupIds.includes(account.groupId));
        groupAddresses.push(...groups.map(account => getAccountAddress(account)));

        knownAccounts[chain] = chainAccounts.filter(
          account => !(
            addresses.includes(getAccountAddress(account)) || (account.groupId && groupIds.includes(account.groupId))
          ),
        );
      }

      const chainBalances = knownBalances[chain];
      if (!chainBalances)
        continue;

      for (const address of [...addresses, ...groupAddresses].filter(uniqueStrings)) {
        if (chainBalances[address])
          delete chainBalances[address];
      }
      knownBalances[chain] = chainBalances;
    }

    set(accounts, knownAccounts);
    set(balances, knownBalances);
  };

  const updateBalances = (chain: string, { perAccount }: BlockchainBalances): void => {
    const data = perAccount[camelCase(chain)] ?? {};
    set(balances, {
      ...get(balances),
      [chain]: data,
    });
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    set(balances, updateBlockchainAssetBalances(balances, prices));
  };

  const getAccounts = (chain: string): BlockchainAccount[] => get(accounts)[chain] ?? [];

  const getAddressBalances = (chain: string, address: string): BlockchainTotals =>
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

  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();

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
        assets: Object.entries(get(mergeAssociatedAssets(assets, getAssociatedAssetIdentifier))).map(([asset, balance]) => ({ asset, ...balance })),
        liabilities: !liabilities ? [] : Object.entries(get(mergeAssociatedAssets(liabilities, getAssociatedAssetIdentifier))).map(([asset, balance]) => ({ asset, ...balance })),
      };
    }

    return {
      assets: [],
      liabilities: [],
    };
  };

  const fetchAccounts = async (
    payload: MaybeRef<BlockchainAccountRequestPayload>,
  ): Promise<Collection<BlockchainAccountGroupWithBalance>> => new Promise((resolve) => {
    resolve(sortAndFilterAccounts(
      get(groups),
      get(payload),
      {
        getAccounts(groupId: string) {
          return blockchainAccountList(get(blockchainAccounts)).filter(account => account.groupId === groupId);
        },
        getLabel(address, chain) {
          return get(addressNameSelector(address, chain));
        },
      },
    ));
  });

  const fetchGroupAccounts = async (
    payload: MaybeRef<BlockchainAccountGroupRequestPayload>,
  ): Promise<Collection<BlockchainAccountWithBalance>> => new Promise((resolve) => {
    const params = get(payload);
    const newVar = blockchainAccountList(get(blockchainAccounts)).filter(account => account.groupId === params.groupId);
    resolve(sortAndFilterAccounts(newVar, params, {
      getLabel(address, chain) {
        return get(addressNameSelector(address, chain));
      },
    }));
  });

  const accountTags = (address: string): ComputedRef<string[]> => computed(() => {
    const account = blockchainAccountList(get(blockchainAccounts))
      .find(account => getAccountAddress(account) === address);
    return account?.tags ?? [];
  });

  return {
    accounts,
    accountTags,
    addresses,
    balances,
    blockchainAccountList,
    blockchainAccounts,
    blockchainTotals,
    fetchAccounts,
    fetchGroupAccounts,
    getAccountByAddress,
    getAccountDetails,
    getAccounts,
    getAddressBalances,
    getAddresses,
    getBlockchainAccounts,
    groups,
    removeAccounts,
    removeTag,
    updateAccountData,
    updateAccounts,
    updateBalances,
    updatePrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainStore, import.meta.hot));
