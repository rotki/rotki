import type { AccountPayload, Accounts, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { removeTags, renameTags } from '@/modules/tags/tag-utils';

export const useBlockchainAccountsStore = defineStore('blockchain/accounts', () => {
  const accounts = ref<Accounts>({});
  const recentlyAddedAddresses = ref<Set<string>>(new Set());

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

  const getAccounts = (chain: string): BlockchainAccount[] => get(accounts)[chain] ?? [];

  const getAccountByAddress = (address: string, chain?: string): BlockchainAccount | undefined => {
    const knownAccounts = get(accounts);
    if (chain && knownAccounts[chain])
      return knownAccounts[chain].find(account => getAccountAddress(account) === address);

    return Object.values(knownAccounts)
      .flatMap(x => x)
      .find(account => getAccountAddress(account) === address);
  };

  const removeTag = (tag: string): void => {
    const copy = { ...get(accounts) };
    for (const chain in copy) {
      const accountData = copy[chain];
      copy[chain] = removeTags(accountData, tag);
    }

    set(accounts, copy);
  };

  const renameTag = (oldName: string, newName: string): void => {
    const copy = { ...get(accounts) };
    for (const chain in copy) {
      const accountData = copy[chain];
      copy[chain] = renameTags(accountData, oldName, newName);
    }

    set(accounts, copy);
  };

  const trackAddedAddresses = (addresses: string[], ttl: number = 60_000): void => {
    const current = new Set(get(recentlyAddedAddresses));
    addresses.forEach(a => current.add(a));
    set(recentlyAddedAddresses, current);

    setTimeout(() => {
      const updated = new Set(get(recentlyAddedAddresses));
      addresses.forEach(a => updated.delete(a));
      set(recentlyAddedAddresses, updated);
    }, ttl);
  };

  return {
    accounts,
    getAccountByAddress,
    getAccounts,
    recentlyAddedAddresses,
    removeTag,
    renameTag,
    trackAddedAddresses,
    updateAccountData,
    updateAccounts,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainAccountsStore, import.meta.hot));
