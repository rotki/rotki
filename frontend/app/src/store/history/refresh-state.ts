import type { Exchange } from '@/types/exchanges';
import type { ChainAddress } from '@/types/history/events';
import { get, set } from '@vueuse/core';
import { logger } from '@/utils/logging';

export const useHistoryRefreshStateStore = defineStore('history/refresh-state', () => {
  const isRefreshing = ref<boolean>(false);
  const lastRefreshTime = ref<number | null>(null);
  const refreshedKeys = ref<Set<string>>(new Set<string>());
  const pendingKeys = ref<Set<string>>(new Set<string>());

  // Prefix keys to distinguish accounts from exchanges
  const BLOCKCHAIN_PREFIX = 'blockchain:';
  const EXCHANGE_PREFIX = 'exchange:';

  const createAccountKey = (account: ChainAddress): string => `${BLOCKCHAIN_PREFIX}${account.chain}:${account.address}`;
  const createExchangeKey = (exchange: Exchange): string => `${EXCHANGE_PREFIX}${exchange.location}:${exchange.name}`;

  const startRefresh = (accounts: Array<ChainAddress>, exchanges: Array<Exchange> = []): void => {
    const newKeys = [
      ...accounts.map(createAccountKey),
      ...exchanges.map(createExchangeKey),
    ];

    // Add new items to refreshed set
    const updated = new Set([...get(refreshedKeys), ...newKeys]);
    set(refreshedKeys, updated);
    set(isRefreshing, true);
    set(lastRefreshTime, Date.now());
    set(pendingKeys, new Set<string>()); // Clear pending
  };

  const finishRefresh = (): void => {
    set(isRefreshing, false);
  };

  const addPendingAccounts = (accounts: Array<ChainAddress>): void => {
    const currentRefreshed = get(refreshedKeys);
    const newPending = new Set(get(pendingKeys));

    accounts.forEach((account) => {
      const key = createAccountKey(account);
      if (!currentRefreshed.has(key)) {
        newPending.add(key);
      }
    });

    set(pendingKeys, newPending);
  };

  const addPendingExchanges = (exchanges: Array<Exchange>): void => {
    const currentRefreshed = get(refreshedKeys);
    const newPending = new Set(get(pendingKeys));

    exchanges.forEach((exchange) => {
      const key = createExchangeKey(exchange);
      if (!currentRefreshed.has(key)) {
        newPending.add(key);
      }
    });

    set(pendingKeys, newPending);
  };

  const getNewAccounts = (currentAccounts: Array<ChainAddress>): Array<ChainAddress> => {
    const currentRefreshed = get(refreshedKeys);

    const newAccounts = currentAccounts.filter((account) => {
      const key = createAccountKey(account);
      return !currentRefreshed.has(key);
    });

    logger.debug(`Checking for new accounts. Current: ${currentAccounts.length}, Refreshed: ${currentRefreshed.size}, New: ${newAccounts.length}`);
    return newAccounts;
  };

  const getNewExchanges = (currentExchanges: Array<Exchange>): Array<Exchange> => {
    const currentRefreshed = get(refreshedKeys);

    const newExchanges = currentExchanges.filter((exchange) => {
      const key = createExchangeKey(exchange);
      return !currentRefreshed.has(key);
    });

    logger.debug(`Checking for new exchanges. Current: ${currentExchanges.length}, Refreshed: ${currentRefreshed.size}, New: ${newExchanges.length}`);
    return newExchanges;
  };

  const getPendingAccountsForRefresh = (): Array<ChainAddress> => {
    const pending = Array.from(get(pendingKeys)).filter(key => key.startsWith(BLOCKCHAIN_PREFIX));
    const result: Array<ChainAddress> = [];

    pending.forEach((key) => {
      // Format: "blockchain:chain:address"
      const parts = key.slice(BLOCKCHAIN_PREFIX.length);
      const colonIndex = parts.indexOf(':');
      const chain = parts.substring(0, colonIndex);
      const address = parts.substring(colonIndex + 1);

      result.push({ address, chain });
    });

    return result;
  };

  const getPendingExchangesForRefresh = (): Array<Exchange> => {
    const pending = Array.from(get(pendingKeys)).filter(key => key.startsWith(EXCHANGE_PREFIX));
    const result: Array<Exchange> = [];

    pending.forEach((key) => {
      // Format: "exchange:location:name"
      const parts = key.slice(EXCHANGE_PREFIX.length);
      const colonIndex = parts.indexOf(':');
      const location = parts.substring(0, colonIndex);
      const name = parts.substring(colonIndex + 1);

      result.push({ location, name });
    });

    return result;
  };

  const hasPendingAccounts = computed<boolean>(() =>
    Array.from(get(pendingKeys)).some(key => key.startsWith(BLOCKCHAIN_PREFIX)),
  );

  const hasPendingExchanges = computed<boolean>(() =>
    Array.from(get(pendingKeys)).some(key => key.startsWith(EXCHANGE_PREFIX)),
  );

  const shouldRefreshAll = (
    currentAccounts: Array<ChainAddress>,
    currentExchanges: Array<Exchange>,
  ): boolean => {
    if (get(lastRefreshTime) === null) {
      return true;
    }

    if (!get(isRefreshing)) {
      const newAccounts = getNewAccounts(currentAccounts);
      const newExchanges = getNewExchanges(currentExchanges);
      return newAccounts.length > 0 || newExchanges.length > 0;
    }

    return false;
  };

  const reset = (): void => {
    set(refreshedKeys, new Set<string>());
    set(pendingKeys, new Set<string>());
    set(isRefreshing, false);
    set(lastRefreshTime, null);
  };

  return {
    addPendingAccounts,
    addPendingExchanges,
    finishRefresh,
    getNewAccounts,
    getNewExchanges,
    getPendingAccountsForRefresh,
    getPendingExchangesForRefresh,
    hasPendingAccounts,
    hasPendingExchanges,
    isRefreshing,
    lastRefreshTime,
    pendingKeys,
    refreshedKeys,
    reset,
    shouldRefreshAll,
    startRefresh,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoryRefreshStateStore, import.meta.hot));
