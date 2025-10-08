import type { ChainAddress } from '@/types/history/events';
import { get, set } from '@vueuse/core';
import { logger } from '@/utils/logging';

export const useHistoryRefreshStateStore = defineStore('history/refresh-state', () => {
  const isRefreshing = ref<boolean>(false);
  const lastRefreshTime = ref<number | null>(null);
  const accountsAtLastRefresh = ref<Set<string>>(new Set<string>());
  const pendingAccounts = ref<Set<string>>(new Set<string>());
  const accountsBeingRefreshed = ref<Set<string>>(new Set<string>());

  const createAccountKey = (account: ChainAddress): string => `${account.chain}:${account.address}`;

  const startRefresh = (accounts: Array<ChainAddress>): void => {
    const accountKeys = new Set(accounts.map(createAccountKey));

    // Merge with existing accounts if we're refreshing pending accounts
    const mergedAccountKeys = new Set([...get(accountsAtLastRefresh), ...accountKeys]);

    // Mark these accounts as being refreshed
    const newAccountsBeingRefreshed = new Set([...get(accountsBeingRefreshed), ...accountKeys]);

    set(accountsAtLastRefresh, mergedAccountKeys);
    set(accountsBeingRefreshed, newAccountsBeingRefreshed);
    set(isRefreshing, true);
    set(lastRefreshTime, Date.now());
    set(pendingAccounts, new Set<string>());
  };

  const finishRefresh = (): void => {
    // Clear the accounts being refreshed
    set(accountsBeingRefreshed, new Set<string>());
    set(isRefreshing, false);

    // If there are pending accounts, keep them for next refresh
    // No need to update pendingAccounts as they're already set
  };

  const addPendingAccounts = (accounts: Array<ChainAddress>): void => {
    const currentAccountsAtLastRefresh = get(accountsAtLastRefresh);
    const currentAccountsBeingRefreshed = get(accountsBeingRefreshed);
    const newPendingAccounts = new Set(get(pendingAccounts));

    accounts.forEach((account) => {
      const key = createAccountKey(account);
      // Only add to pending if not already refreshed AND not currently being refreshed
      if (!currentAccountsAtLastRefresh.has(key) && !currentAccountsBeingRefreshed.has(key)) {
        newPendingAccounts.add(key);
      }
    });

    set(pendingAccounts, newPendingAccounts);
  };

  const getNewAccounts = (
    currentAccounts: Array<ChainAddress>,
  ): Array<ChainAddress> => {
    const lastRefreshedAccounts = get(accountsAtLastRefresh);
    const currentAccountsBeingRefreshed = get(accountsBeingRefreshed);

    logger.debug(`Checking for new accounts. Current: ${currentAccounts.length}, Last refreshed: ${lastRefreshedAccounts.size}, Being refreshed: ${currentAccountsBeingRefreshed.size}`);

    return currentAccounts.filter((account) => {
      const key = createAccountKey(account);
      // Exclude accounts that have been refreshed OR are currently being refreshed
      return !lastRefreshedAccounts.has(key) && !currentAccountsBeingRefreshed.has(key);
    });
  };

  const getPendingAccountsForRefresh = (): Array<ChainAddress> => {
    const currentAccountsBeingRefreshed = get(accountsBeingRefreshed);
    // Filter out accounts that are currently being refreshed
    const pendingKeys = Array.from(get(pendingAccounts)).filter(key => !currentAccountsBeingRefreshed.has(key));
    const result: Array<ChainAddress> = [];

    pendingKeys.forEach((key) => {
      const [chain, address] = key.split(':');
      result.push({ address, chain });
    });

    return result;
  };

  const hasPendingAccounts = computed<boolean>(() => get(pendingAccounts).size > 0);

  const shouldRefreshAll = (
    currentAccounts: Array<ChainAddress>,
  ): boolean => {
    // If never refreshed, refresh all
    if (get(lastRefreshTime) === null) {
      return true;
    }

    // If not currently refreshing and there are new accounts, refresh all
    if (!get(isRefreshing)) {
      const newAccounts = getNewAccounts(currentAccounts);
      return newAccounts.length > 0;
    }

    return false;
  };

  const reset = (): void => {
    set(accountsAtLastRefresh, new Set<string>());
    set(accountsBeingRefreshed, new Set<string>());
    set(isRefreshing, false);
    set(lastRefreshTime, null);
    set(pendingAccounts, new Set<string>());
  };

  return {
    accountsAtLastRefresh,
    accountsBeingRefreshed,
    addPendingAccounts,
    finishRefresh,
    getNewAccounts,
    getPendingAccountsForRefresh,
    hasPendingAccounts,
    isRefreshing,
    lastRefreshTime,
    pendingAccounts,
    reset,
    shouldRefreshAll,
    startRefresh,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoryRefreshStateStore, import.meta.hot));
