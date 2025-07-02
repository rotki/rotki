import type {
  Accounts,
  Balances,
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
} from '@/types/blockchain/accounts';
import type { ProtocolBalances } from '@/types/blockchain/balances';
import type { Collection } from '@/types/collection';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSupportedChains } from '@/composables/info/chains';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { getAccountBalance, hasTokens, sortAndFilterAccounts } from '@/utils/blockchain/accounts';
import { createAccountWithBalance } from '@/utils/blockchain/accounts/create-account-with-balance';
import { getAccountAddress, getAccountLabel } from '@/utils/blockchain/accounts/utils';
import { assetSum, balanceSum } from '@/utils/calculation';
import { uniqueStrings } from '@/utils/data';
import { type AssetBalance, type Balance, Blockchain, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';

interface AccountBalances {
  assets: AssetBalance[];
  liabilities: AssetBalance[];
}

interface UseBlockchainAccountDataReturn {
  fetchAccounts: (payload: MaybeRef<BlockchainAccountRequestPayload>) => Promise<Collection<BlockchainAccountGroupWithBalance>>;
  fetchGroupAccounts: (payload: MaybeRef<BlockchainAccountGroupRequestPayload>) => Promise<Collection<BlockchainAccountWithBalance>>;
  getAccounts: () => BlockchainAccountGroupWithBalance[];
  getAccountDetails: (chain: string, address: string) => AccountBalances;
  getBlockchainAccounts: (chain: string) => BlockchainAccountWithBalance[];
  useAccountTags: (address: MaybeRef<string>) => ComputedRef<string[]>;
  getAccountList: (accountData: Accounts, balanceData: Balances) => BlockchainAccountWithBalance[];
}

function toAssetBalances(
  balances: Record<string, ProtocolBalances>,
  isIgnored: (asset: string) => boolean,
  assetAssociationMap: Record<string, string>,
): AssetBalance[] {
  const intermediate: Record<string, Balance> = {};
  for (const [assetIdentifier, balance] of Object.entries(balances)) {
    const identifier = assetAssociationMap?.[assetIdentifier] ?? assetIdentifier;
    if (isIgnored(identifier))
      continue;

    for (const protocol in balance) {
      if (balance[protocol].amount.isZero())
        continue;

      if (!intermediate[identifier]) {
        intermediate[identifier] = balance[protocol];
      }
      else {
        intermediate[identifier] = balanceSum(intermediate[identifier], balance[protocol]);
      }
    }
  }
  return Object.entries(intermediate).map(([asset, balance]) => ({ asset, ...balance } satisfies AssetBalance));
}

export function useBlockchainAccountData(): UseBlockchainAccountDataReturn {
  const { balances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { addressNameSelector } = useAddressesNamesStore();
  const { getChainAccountType } = useSupportedChains();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { assetAssociationMap } = useAssetInfoRetrieval();

  const getAccountBalances = (
    balances: Balances,
    chain: string,
    address: string,
    assetAssociationMap: Record<string, string>,
  ): AccountBalances => {
    const chainAssets = balances[chain] ?? {};
    const addressAssets = chainAssets[address];

    if (addressAssets) {
      const { assets, liabilities } = addressAssets;

      return {
        assets: toAssetBalances(assets, isAssetIgnored, assetAssociationMap),
        liabilities: !liabilities ? [] : toAssetBalances(liabilities, isAssetIgnored, assetAssociationMap),
      };
    }

    return {
      assets: [],
      liabilities: [],
    };
  };

  const getAccountDetails = (
    chain: string,
    address: string,
  ): AccountBalances => getAccountBalances(get(balances), get(chain), get(address), get(assetAssociationMap));

  const useAccountTags = (address: MaybeRef<string>): ComputedRef<string[]> => computed<string[]>(() => {
    const accountData = get(accounts);
    const accountAddress = get(address);
    const tags: Set<string> = new Set();

    for (const accounts of Object.values(accountData)) {
      for (const account of accounts) {
        if (getAccountAddress(account) !== accountAddress || !account.tags)
          continue;

        for (const tag of account.tags) {
          tags.add(tag);
        }
      }
    }
    return Array.from(tags);
  });

  const getBlockchainAccounts = (chain: string): BlockchainAccountWithBalance[] => {
    const accountData = get(accounts)[chain];
    const balanceData = get(balances)[chain];

    if (!accountData || accountData.length === 0) {
      return [];
    }

    const accountsWithBalances: BlockchainAccountWithBalance[] = [];
    for (const account of accountData) {
      if (account.data.type === 'xpub')
        continue;
      accountsWithBalances.push(createAccountWithBalance(account, balanceData));
    }
    return accountsWithBalances;
  };

  const getGroups = (accounts: Accounts, balances: Balances): BlockchainAccountGroupWithBalance[] => {
    const accountData = omit(accounts, [Blockchain.ETH2]);
    const balanceData = omit(balances, [Blockchain.ETH2]);

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
  };

  const getAccounts = (): BlockchainAccountGroupWithBalance[] => getGroups(get(accounts), get(balances));

  function getAccountList(accountData: Accounts, balanceData: Balances): BlockchainAccountWithBalance[] {
    const entries: BlockchainAccountWithBalance[] = [];
    for (const [chain, accounts] of Object.entries(accountData)) {
      const chainBalances = balanceData[chain] ?? {};
      for (const account of accounts) {
        if (!account.groupHeader) {
          entries.push(createAccountWithBalance(account, chainBalances));
        }
      }
    }
    return entries;
  }

  const fetchAccounts = async (
    payload: MaybeRef<BlockchainAccountRequestPayload>,
  ): Promise<Collection<BlockchainAccountGroupWithBalance>> => new Promise((resolve) => {
    const accountData = get(accounts);
    const balanceData = get(balances);
    const blockchainAccounts = getAccountList(accountData, balanceData);
    const groups = getGroups(accountData, balanceData);

    resolve(sortAndFilterAccounts(
      groups,
      get(payload),
      {
        getAccounts(groupId: string) {
          return blockchainAccounts.filter(account => account.groupId === groupId);
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
    const accountData = get(accounts);
    const balanceData = get(balances);
    const blockchainAccounts = getAccountList(accountData, balanceData);
    const groupAccounts = blockchainAccounts.filter(account => account.groupId === params.groupId);
    resolve(sortAndFilterAccounts(groupAccounts, params, {
      getLabel(address, chain) {
        return get(addressNameSelector(address, chain));
      },
    }));
  });

  return {
    fetchAccounts,
    fetchGroupAccounts,
    getAccountDetails,
    getAccountList,
    getAccounts,
    getBlockchainAccounts,
    useAccountTags,
  };
}
