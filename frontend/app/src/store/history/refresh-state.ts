import type { Exchange } from '@/types/exchanges';
import type { ChainAddress } from '@/types/history/events';
import { get, set } from '@vueuse/core';
import { logger } from '@/utils/logging';

export const useHistoryRefreshStateStore = defineStore('history/refresh-state', () => {
  const isRefreshing = ref<boolean>(false);
  const lastRefreshTime = ref<number | null>(null);
  const accountsAtLastRefresh = ref<Set<string>>(new Set<string>());
  const pendingAccounts = ref<Set<string>>(new Set<string>());
  const accountsBeingRefreshed = ref<Set<string>>(new Set<string>());
  const exchangesAtLastRefresh = ref<Set<string>>(new Set<string>());
  const pendingExchanges = ref<Set<string>>(new Set<string>());
  const exchangesBeingRefreshed = ref<Set<string>>(new Set<string>());

  const createAccountKey = (account: ChainAddress): string => `${account.chain}:${account.address}`;

  const createExchangeKey = (exchange: Exchange): string => `${exchange.location}:${exchange.name}`;

  const startRefresh = (accounts: Array<ChainAddress>, exchanges: Array<Exchange> = []): void => {
    const accountKeys = new Set(accounts.map(createAccountKey));
    const exchangeKeys = new Set(exchanges.map(createExchangeKey));

    // Merge with existing accounts/exchanges if we're refreshing pending ones
    const mergedAccountKeys = new Set([...get(accountsAtLastRefresh), ...accountKeys]);
    const mergedExchangeKeys = new Set([...get(exchangesAtLastRefresh), ...exchangeKeys]);

    // Mark these accounts/exchanges as being refreshed
    const newAccountsBeingRefreshed = new Set([...get(accountsBeingRefreshed), ...accountKeys]);
    const newExchangesBeingRefreshed = new Set([...get(exchangesBeingRefreshed), ...exchangeKeys]);

    set(accountsAtLastRefresh, mergedAccountKeys);
    set(exchangesAtLastRefresh, mergedExchangeKeys);
    set(accountsBeingRefreshed, newAccountsBeingRefreshed);
    set(exchangesBeingRefreshed, newExchangesBeingRefreshed);
    set(isRefreshing, true);
    set(lastRefreshTime, Date.now());
    set(pendingAccounts, new Set<string>());
    set(pendingExchanges, new Set<string>());
  };

  const finishRefresh = (): void => {
    // Clear the accounts/exchanges being refreshed
    set(accountsBeingRefreshed, new Set<string>());
    set(exchangesBeingRefreshed, new Set<string>());
    set(isRefreshing, false);

    // If there are pending accounts/exchanges, keep them for next refresh
    // No need to update pendingAccounts/pendingExchanges as they're already set
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

  const addPendingExchanges = (exchanges: Array<Exchange>): void => {
    const currentExchangesAtLastRefresh = get(exchangesAtLastRefresh);
    const currentExchangesBeingRefreshed = get(exchangesBeingRefreshed);
    const newPendingExchanges = new Set(get(pendingExchanges));

    exchanges.forEach((exchange) => {
      const key = createExchangeKey(exchange);
      // Only add to pending if not already refreshed AND not currently being refreshed
      if (!currentExchangesAtLastRefresh.has(key) && !currentExchangesBeingRefreshed.has(key)) {
        newPendingExchanges.add(key);
      }
    });

    set(pendingExchanges, newPendingExchanges);
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

  const getNewExchanges = (
    currentExchanges: Array<Exchange>,
  ): Array<Exchange> => {
    const lastRefreshedExchanges = get(exchangesAtLastRefresh);
    const currentExchangesBeingRefreshed = get(exchangesBeingRefreshed);

    logger.debug(`Checking for new exchanges. Current: ${currentExchanges.length}, Last refreshed: ${lastRefreshedExchanges.size}, Being refreshed: ${currentExchangesBeingRefreshed.size}`);

    return currentExchanges.filter((exchange) => {
      const key = createExchangeKey(exchange);
      // Exclude exchanges that have been refreshed OR are currently being refreshed
      return !lastRefreshedExchanges.has(key) && !currentExchangesBeingRefreshed.has(key);
    });
  };

  const getPendingAccountsForRefresh = (): Array<ChainAddress> => {
    const currentAccountsBeingRefreshed = get(accountsBeingRefreshed);
    // Filter out accounts that are currently being refreshed
    const pendingKeys = Array.from(get(pendingAccounts)).filter(key => !currentAccountsBeingRefreshed.has(key));
    const result: Array<ChainAddress> = [];

    pendingKeys.forEach((key) => {
      const colonIndex = key.indexOf(':');
      const chain = key.substring(0, colonIndex);
      const address = key.substring(colonIndex + 1);
      result.push({ address, chain });
    });

    return result;
  };

  const getPendingExchangesForRefresh = (): Array<Exchange> => {
    const currentExchangesBeingRefreshed = get(exchangesBeingRefreshed);
    // Filter out exchanges that are currently being refreshed
    const pendingKeys = Array.from(get(pendingExchanges)).filter(key => !currentExchangesBeingRefreshed.has(key));
    const result: Array<Exchange> = [];

    pendingKeys.forEach((key) => {
      const colonIndex = key.indexOf(':');
      const location = key.substring(0, colonIndex);
      const name = key.substring(colonIndex + 1);
      result.push({ location, name });
    });

    return result;
  };

  const hasPendingAccounts = computed<boolean>(() => get(pendingAccounts).size > 0);

  const hasPendingExchanges = computed<boolean>(() => get(pendingExchanges).size > 0);

  const shouldRefreshAll = (
    currentAccounts: Array<ChainAddress>,
    currentExchanges: Array<Exchange>,
  ): boolean => {
    // If never refreshed, refresh all
    if (get(lastRefreshTime) === null) {
      return true;
    }

    // If not currently refreshing and there are new accounts or exchanges, refresh all
    if (!get(isRefreshing)) {
      const newAccounts = getNewAccounts(currentAccounts);
      const newExchanges = getNewExchanges(currentExchanges);
      return newAccounts.length > 0 || newExchanges.length > 0;
    }

    return false;
  };

  const reset = (): void => {
    set(accountsAtLastRefresh, new Set<string>());
    set(accountsBeingRefreshed, new Set<string>());
    set(exchangesAtLastRefresh, new Set<string>());
    set(exchangesBeingRefreshed, new Set<string>());
    set(isRefreshing, false);
    set(lastRefreshTime, null);
    set(pendingAccounts, new Set<string>());
    set(pendingExchanges, new Set<string>());
  };

  return {
    accountsAtLastRefresh,
    accountsBeingRefreshed,
    addPendingAccounts,
    addPendingExchanges,
    exchangesAtLastRefresh,
    exchangesBeingRefreshed,
    finishRefresh,
    getNewAccounts,
    getNewExchanges,
    getPendingAccountsForRefresh,
    getPendingExchangesForRefresh,
    hasPendingAccounts,
    hasPendingExchanges,
    isRefreshing,
    lastRefreshTime,
    pendingAccounts,
    pendingExchanges,
    reset,
    shouldRefreshAll,
    startRefresh,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoryRefreshStateStore, import.meta.hot));
