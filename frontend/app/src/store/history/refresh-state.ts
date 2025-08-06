import type { BitcoinChainAddress, EvmChainAddress } from '@/types/history/events';
import { get, set } from '@vueuse/core';
import { logger } from '@/utils/logging';

interface RefreshState {
  isRefreshing: boolean;
  lastRefreshTime: number | null;
  accountsAtLastRefresh: Set<string>;
  pendingAccounts: Set<string>;
  accountsBeingRefreshed: Set<string>;
}

export const useHistoryRefreshStateStore = defineStore('history/refresh-state', () => {
  const state = ref<RefreshState>({
    accountsAtLastRefresh: new Set<string>(),
    accountsBeingRefreshed: new Set<string>(),
    isRefreshing: false,
    lastRefreshTime: null,
    pendingAccounts: new Set<string>(),
  });

  const isRefreshing = computed<boolean>(() => get(state).isRefreshing);
  const lastRefreshTime = computed<number | null>(() => get(state).lastRefreshTime);
  const accountsAtLastRefresh = computed<Set<string>>(() => get(state).accountsAtLastRefresh);
  const pendingAccounts = computed<Set<string>>(() => get(state).pendingAccounts);
  const accountsBeingRefreshed = computed<Set<string>>(() => get(state).accountsBeingRefreshed);

  const createAccountKey = (account: EvmChainAddress | BitcoinChainAddress): string => {
    if ('evmChain' in account) {
      return `${account.evmChain}:${account.address}`;
    }
    return `${account.chain}:${account.address}`;
  };

  const startRefresh = (accounts: Array<EvmChainAddress | BitcoinChainAddress>): void => {
    const currentState = get(state);
    const accountKeys = new Set(accounts.map(createAccountKey));

    // Merge with existing accounts if we're refreshing pending accounts
    const mergedAccountKeys = new Set([...currentState.accountsAtLastRefresh, ...accountKeys]);

    // Mark these accounts as being refreshed
    const newAccountsBeingRefreshed = new Set([...currentState.accountsBeingRefreshed, ...accountKeys]);

    logger.info(`Starting refresh for ${accounts.length} accounts, total tracked: ${mergedAccountKeys.size}`);

    set(state, {
      accountsAtLastRefresh: mergedAccountKeys,
      accountsBeingRefreshed: newAccountsBeingRefreshed,
      isRefreshing: true,
      lastRefreshTime: Date.now(),
      pendingAccounts: new Set<string>(),
    });
  };

  const finishRefresh = (): void => {
    const currentState = get(state);
    const pendingAccountKeys = currentState.pendingAccounts;

    // If there are pending accounts, move them to be refreshed next
    if (pendingAccountKeys.size > 0) {
      set(state, {
        accountsAtLastRefresh: currentState.accountsAtLastRefresh,
        accountsBeingRefreshed: new Set<string>(), // Clear the accounts being refreshed
        isRefreshing: false,
        lastRefreshTime: currentState.lastRefreshTime,
        pendingAccounts: pendingAccountKeys,
      });
    }
    else {
      set(state, {
        ...currentState,
        accountsBeingRefreshed: new Set<string>(), // Clear the accounts being refreshed
        isRefreshing: false,
      });
    }
  };

  const addPendingAccounts = (accounts: Array<EvmChainAddress | BitcoinChainAddress>): void => {
    const currentState = get(state);
    const newPendingAccounts = new Set(currentState.pendingAccounts);

    accounts.forEach((account) => {
      const key = createAccountKey(account);
      // Only add to pending if not already refreshed AND not currently being refreshed
      if (!currentState.accountsAtLastRefresh.has(key) && !currentState.accountsBeingRefreshed.has(key)) {
        newPendingAccounts.add(key);
      }
    });

    set(state, {
      ...currentState,
      pendingAccounts: newPendingAccounts,
    });
  };

  const getNewAccounts = (
    currentAccounts: Array<EvmChainAddress | BitcoinChainAddress>,
  ): Array<EvmChainAddress | BitcoinChainAddress> => {
    const currentState = get(state);
    const lastRefreshedAccounts = currentState.accountsAtLastRefresh;
    const accountsBeingRefreshed = currentState.accountsBeingRefreshed;

    logger.debug(`Checking for new accounts. Current: ${currentAccounts.length}, Last refreshed: ${lastRefreshedAccounts.size}, Being refreshed: ${accountsBeingRefreshed.size}`);

    const newAccounts = currentAccounts.filter((account) => {
      const key = createAccountKey(account);
      // Exclude accounts that have been refreshed OR are currently being refreshed
      return !lastRefreshedAccounts.has(key) && !accountsBeingRefreshed.has(key);
    });

    if (newAccounts.length > 0) {
      logger.info(`Found ${newAccounts.length} new accounts (excluding ${accountsBeingRefreshed.size} being refreshed)`, newAccounts.map(createAccountKey));
    }

    return newAccounts;
  };

  const getPendingAccountsForRefresh = (): Array<EvmChainAddress | BitcoinChainAddress> => {
    const currentState = get(state);
    const accountsBeingRefreshed = currentState.accountsBeingRefreshed;
    // Filter out accounts that are currently being refreshed
    const pendingKeys = Array.from(currentState.pendingAccounts).filter(key => !accountsBeingRefreshed.has(key));
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
      logger.info(`Preparing ${result.length} pending accounts for refresh (excluded ${accountsBeingRefreshed.size} being refreshed)`);
    }

    return result;
  };

  const hasPendingAccounts = computed<boolean>(() => get(state).pendingAccounts.size > 0);

  const shouldRefreshAll = (
    currentAccounts: Array<EvmChainAddress | BitcoinChainAddress>,
  ): boolean => {
    const currentState = get(state);

    // If never refreshed, refresh all
    if (currentState.lastRefreshTime === null) {
      return true;
    }

    // If not currently refreshing and there are new accounts, refresh all
    if (!currentState.isRefreshing) {
      const newAccounts = getNewAccounts(currentAccounts);
      return newAccounts.length > 0;
    }

    return false;
  };

  const reset = (): void => {
    set(state, {
      accountsAtLastRefresh: new Set<string>(),
      accountsBeingRefreshed: new Set<string>(),
      isRefreshing: false,
      lastRefreshTime: null,
      pendingAccounts: new Set<string>(),
    });
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
