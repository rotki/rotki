import type { MaybeRef } from 'vue';
import type { BalanceSource, RefreshOutcome } from '@/modules/balances/refresh/core/refresh-types';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { createBalanceRefresher } from '@/modules/balances/refresh/core/balance-refresher';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useBanks } from '@/modules/banks/use-banks';
import { arrayify } from '@/modules/core/common/data/array';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { BlockchainRefreshButtonBehaviour } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';

/**
 * Logs what the stores could not report themselves: a port that threw or rejected.
 *
 * @remarks
 * The stores already notify the user about the failures they handle, so this only keeps an
 * unexpected rejection visible now that the refresher no longer lets it escape.
 */
function logFailures(outcome: RefreshOutcome): void {
  if (outcome.ok)
    return;

  for (const failure of outcome.error)
    logger.error(`${failure.source} refresh failed`, failure.cause);
}

/**
 * The app's balance refresh, wired to the stores.
 *
 * @remarks
 * Everything reaching this composable came from a user pressing something, so chains are queried
 * in `user` mode, which supersedes a background run rather than joining it: a user asking for fresh
 * data must not silently receive the periodic tick's result. The refresh logic itself lives in
 * `refresh/core`, which never sees a store.
 */
export const useBalanceRefresh = createSharedComposable(() => {
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { fetchConnectedExchangeBalances, fetchSelectedExchangeBalances } = useExchanges();
  const { fetchBankBalances, refreshBankConnections } = useBanks();
  const { fetchManualBalances } = useManualBalances();
  const { detectAllTokens } = useTokenDetectionOrchestrator();
  const { refreshPrices } = usePriceRefresh();
  const { supportedChains, supportsTransactions } = useSupportedChains();
  const blockchainRefreshButtonBehaviour = useSetting('blockchainRefreshButtonBehaviour');

  const refresher = createBalanceRefresher({
    detectTokens: async chains => detectAllTokens([...chains]),
    /** The balance query is a no-op without connections, so a refresh before any page listed them would never recover. */
    queryBanks: async () => {
      await refreshBankConnections();
      await fetchBankBalances(true);
    },
    queryChains: async chains => refreshBlockchainBalances({ blockchain: [...chains] }, RefreshMode.USER),
    queryExchanges: async () => fetchConnectedExchangeBalances(true),
    queryManual: async () => fetchManualBalances(true),
    redetectByDefault: () => get(blockchainRefreshButtonBehaviour) === BlockchainRefreshButtonBehaviour.REDETECT_TOKENS,
    refreshPrices: async () => refreshPrices(true),
    supportedChains: () => get(supportedChains).map(chain => chain.id),
    supportsDetection: supportsTransactions,
  });

  /**
   * Every source, then prices, never redetecting.
   *
   * @remarks
   * The dashboard offers redetection as its own action, so this ignores the refresh button setting
   * that {@link handleBlockchainRefresh} follows.
   */
  async function refreshAll(): Promise<void> {
    logFailures(await refresher.refreshAll({ redetect: false }));
  }

  async function redetectAndRefreshAll(): Promise<void> {
    logFailures(await refresher.refreshAll({ redetect: true }));
  }

  async function refreshAllPrices(): Promise<void> {
    logFailures(await refresher.refreshPrices());
  }

  /** One balance source, then prices, never redetecting, like {@link refreshAll}. */
  async function refreshSourceAndPrices(source: BalanceSource): Promise<void> {
    logFailures(await refresher.refreshSource(source, { redetect: false }));
  }

  /** Refreshes the given chains, or every chain, following the user's refresh button behaviour. */
  async function handleBlockchainRefresh(blockchain?: MaybeRef<string | string[] | undefined>, forceRedetect = false): Promise<void> {
    const chains = get(blockchain);
    logFailures(await refresher.refreshBlockchain({
      chains: chains ? arrayify(chains) : undefined,
      redetect: forceRedetect ? true : undefined,
    }));
  }

  /** Queries the given chains, or every chain, without token detection. */
  async function refreshChainBalances(blockchain?: string | string[]): Promise<void> {
    logFailures(await refresher.refreshBlockchain({
      chains: blockchain ? arrayify(blockchain) : undefined,
      redetect: false,
    }));
  }

  /** Detection only, for the controls that ask for it by name. */
  async function massDetectTokens(chain?: string | string[]): Promise<void> {
    await detectAllTokens(chain);
  }

  async function refreshExchangeBalances(): Promise<void> {
    await fetchConnectedExchangeBalances(true);
  }

  async function refreshExchangeBalance(exchangeLocation: string): Promise<void> {
    await fetchSelectedExchangeBalances(exchangeLocation);
  }

  return {
    handleBlockchainRefresh,
    massDetectTokens,
    redetectAndRefreshAll,
    refreshAll,
    refreshAllPrices,
    refreshBlockchainBalances: refreshChainBalances,
    refreshExchangeBalance,
    refreshExchangeBalances,
    refreshSourceAndPrices,
  };
});
