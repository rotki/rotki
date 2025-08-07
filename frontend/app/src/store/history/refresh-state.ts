import type { BitcoinChainAddress, EvmChainAddress } from '@/types/history/events';
import { get, set } from '@vueuse/core';
import { logger } from '@/utils/logging';

export const useHistoryRefreshStateStore = defineStore('history/refresh-state', () => {
  const isRefreshing = ref<boolean>(false);
  const lastRefreshTime = ref<number | null>(null);
  const accountsAtLastRefresh = ref<Set<string>>(new Set<string>());
  const pendingAccounts = ref<Set<string>>(new Set<string>());
  const accountsBeingRefreshed = ref<Set<string>>(new Set<string>());

  const createAccountKey = (account: EvmChainAddress | BitcoinChainAddress): string => {
    if ('evmChain' in account) {
      return `${account.evmChain}:${account.address}`;
    }
    return `${account.chain}:${account.address}`;
  };

  const startRefresh = (accounts: Array<EvmChainAddress | BitcoinChainAddress>): void => {
    const accountKeys = new Set(accounts.map(createAccountKey));

    // Merge with existing accounts if we're refreshing pending accounts
    const mergedAccountKeys = new Set([...get(accountsAtLastRefresh), ...accountKeys]);

    // Mark these accounts as being refreshed
    const newAccountsBeingRefreshed = new Set([...get(accountsBeingRefreshed), ...accountKeys]);

    logger.info(`Starting refresh for ${accounts.length} accounts, total tracked: ${mergedAccountKeys.size}`);

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

  const addPendingAccounts = (accounts: Array<EvmChainAddress | BitcoinChainAddress>): void => {
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
    currentAccounts: Array<EvmChainAddress | BitcoinChainAddress>,
  ): Array<EvmChainAddress | BitcoinChainAddress> => {
    const lastRefreshedAccounts = get(accountsAtLastRefresh);
    const currentAccountsBeingRefreshed = get(accountsBeingRefreshed);

    logger.debug(`Checking for new accounts. Current: ${currentAccounts.length}, Last refreshed: ${lastRefreshedAccounts.size}, Being refreshed: ${currentAccountsBeingRefreshed.size}`);

    const newAccounts = currentAccounts.filter((account) => {
      const key = createAccountKey(account);
      // Exclude accounts that have been refreshed OR are currently being refreshed
      return !lastRefreshedAccounts.has(key) && !currentAccountsBeingRefreshed.has(key);
    });

    if (newAccounts.length > 0) {
      logger.info(`Found ${newAccounts.length} new accounts (excluding ${currentAccountsBeingRefreshed.size} being refreshed)`, newAccounts.map(createAccountKey));
    }

    return newAccounts;
  };

  const getPendingAccountsForRefresh = (): Array<EvmChainAddress | BitcoinChainAddress> => {
    const currentAccountsBeingRefreshed = get(accountsBeingRefreshed);
    // Filter out accounts that are currently being refreshed
    const pendingKeys = Array.from(get(pendingAccounts)).filter(key => !currentAccountsBeingRefreshed.has(key));
    const result: Array<EvmChainAddress | BitcoinChainAddress> = [];

    pendingKeys.forEach((key) => {
      const [chain, address] = key.split(':');
      if (chain && address) {
        // Check if it's a bitcoin chain (simple heuristic - could be improved)
        if (chain.toLowerCase() === 'btc' || chain.toLowerCase() === 'bch') {
          result.push({ address, chain });
        }
        else {
          result.push({ address, evmChain: chain });
        }
      }
    });

    if (result.length > 0) {
      logger.info(`Preparing ${result.length} pending accounts for refresh (excluded ${currentAccountsBeingRefreshed.size} being refreshed)`);
    }

    return result;
  };

  const hasPendingAccounts = computed<boolean>(() => get(pendingAccounts).size > 0);

  const shouldRefreshAll = (
    currentAccounts: Array<EvmChainAddress | BitcoinChainAddress>,
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
