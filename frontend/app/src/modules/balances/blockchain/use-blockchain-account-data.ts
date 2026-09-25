import type { AssetBalance } from '@rotki/common';
import type { ComputedRef, MaybeRef, MaybeRefOrGetter } from 'vue';
import type {
  Accounts,
  Balances,
  BlockchainAccountGroupRequestPayload,
  BlockchainAccountGroupWithBalance,
  BlockchainAccountRequestPayload,
  BlockchainAccountWithBalance,
} from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { ok, type Result } from 'plainfp/result';
import { sortAndFilterAccounts } from '@/modules/accounts/account-helpers';
import { getAccountAddress, getAccountLabel, isXpubAccount } from '@/modules/accounts/account-utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { accountAssetBalances, type AccountAssetPorts, accountsByGroup } from '@/modules/accounts/core/account-assets';
import { type AccountGroupPorts, accountGroups } from '@/modules/accounts/core/account-groups';
import { createAccountWithBalance } from '@/modules/accounts/create-account-with-balance';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

interface AccountBalances {
  assets: AssetBalance[];
  liabilities: AssetBalance[];
}

interface UseBlockchainAccountDataReturn {
  /** Pages the accounts already in the store, so it cannot fail. */
  fetchAccounts: (payload: MaybeRef<BlockchainAccountRequestPayload>) => Promise<Result<Collection<BlockchainAccountGroupWithBalance>, never>>;
  /** Pages one group's accounts already in the store, so it cannot fail. */
  fetchGroupAccounts: (payload: MaybeRef<BlockchainAccountGroupRequestPayload>) => Promise<Result<Collection<BlockchainAccountWithBalance>, never>>;
  getAccounts: () => BlockchainAccountGroupWithBalance[];
  getAccountDetails: (chain: string, address: string) => AccountBalances;
  getBlockchainAccounts: (chain: string) => BlockchainAccountWithBalance[];
  useAccountTags: (address: MaybeRefOrGetter<string>) => ComputedRef<string[]>;
  getAccountsByCategory: (category: MaybeRefOrGetter<string>) => ComputedRef<BlockchainAccountGroupWithBalance[]>;
  getAccountList: (accountData: Accounts, balanceData: Balances) => BlockchainAccountWithBalance[];
}

export function useBlockchainAccountData(): UseBlockchainAccountDataReturn {
  const { balances } = storeToRefs(useBalancesStore());
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { getAddressName } = useAddressNameResolution();
  const { getChainAccountType } = useSupportedChains();
  const { isAssetIgnored } = useAssetsStore();
  const resolveIdentifier = useResolveAssetIdentifier();

  const assetPorts: AccountAssetPorts = { isAssetIgnored, resolveIdentifier };
  const groupPorts: AccountGroupPorts = { accountType: getChainAccountType, isAssetIgnored };

  function getAccountDetails(chain: string, address: string): AccountBalances {
    const accountBalances = get(balances)[chain]?.[address];
    return {
      assets: accountBalances ? accountAssetBalances(accountBalances.assets, assetPorts) : [],
      liabilities: accountBalances?.liabilities ? accountAssetBalances(accountBalances.liabilities, assetPorts) : [],
    };
  }

  const useAccountTags = (address: MaybeRefOrGetter<string>): ComputedRef<string[]> => computed<string[]>(() => {
    const accountData = get(accounts);
    const accountAddress = toValue(address);
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
      if (isXpubAccount(account))
        continue;
      accountsWithBalances.push(createAccountWithBalance(account, balanceData, isAssetIgnored));
    }
    return accountsWithBalances;
  };

  const getAccounts = (): BlockchainAccountGroupWithBalance[] => accountGroups(get(accounts), get(balances), groupPorts);

  function getAccountList(accountData: Accounts, balanceData: Balances): BlockchainAccountWithBalance[] {
    const entries: BlockchainAccountWithBalance[] = [];
    for (const [chain, accounts] of Object.entries(accountData)) {
      const chainBalances = balanceData[chain] ?? {};
      for (const account of accounts) {
        if (!account.groupHeader) {
          entries.push(createAccountWithBalance(account, chainBalances, isAssetIgnored));
        }
      }
    }
    return entries;
  }

  const getAccountsByCategory = (category: MaybeRefOrGetter<string>): ComputedRef<BlockchainAccountGroupWithBalance[]> => computed(() => {
    const groups = accountGroups(get(accounts), get(balances), groupPorts);
    return groups.filter(item => item.category === toValue(category));
  });

  const fetchAccounts = async (
    payload: MaybeRef<BlockchainAccountRequestPayload>,
  ): Promise<Result<Collection<BlockchainAccountGroupWithBalance>, never>> => {
    const accountData = get(accounts);
    const balanceData = get(balances);
    const members = accountsByGroup(getAccountList(accountData, balanceData));

    return ok(sortAndFilterAccounts(
      accountGroups(accountData, balanceData, groupPorts),
      get(payload),
      {
        getAccounts(groupId: string) {
          return members.get(groupId) ?? [];
        },
        getLabel(account, chain) {
          return isXpubAccount(account) ? getAccountLabel(account) : getAddressName(getAccountAddress(account), chain);
        },
      },
    ));
  };

  const fetchGroupAccounts = async (
    payload: MaybeRef<BlockchainAccountGroupRequestPayload>,
  ): Promise<Result<Collection<BlockchainAccountWithBalance>, never>> => {
    const params = get(payload);
    const accountData = get(accounts);
    const balanceData = get(balances);
    const blockchainAccounts = getAccountList(accountData, balanceData);
    const groupAccounts = blockchainAccounts.filter(account => account.groupId === params.groupId);
    return ok(sortAndFilterAccounts(groupAccounts, params, {
      getLabel(account, chain) {
        return getAddressName(getAccountAddress(account), chain);
      },
    }));
  };

  return {
    fetchAccounts,
    fetchGroupAccounts,
    getAccountDetails,
    getAccountList,
    getAccounts,
    getAccountsByCategory,
    getBlockchainAccounts,
    useAccountTags,
  };
}
