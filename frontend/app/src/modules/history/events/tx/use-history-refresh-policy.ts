import type { Exchange } from '@/modules/balances/types/exchanges';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import type { StaleAfterEdge } from '@/modules/task-center/core/orchestrator/spec';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryTransactionAccounts } from '@/modules/history/events/tx/use-history-transaction-accounts';
import { Purgeable } from '@/modules/session/purge';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface NoveltyDetection {
  newAccounts: ChainAddress[];
  newExchanges: Exchange[];
}

export interface RefreshTargets {
  accounts: ChainAddress[];
  decodableAccounts: ChainAddress[];
  exchanges: Exchange[];
  fullRefresh: boolean;
  queryExchanges: boolean;
  shouldShowSyncProgress: boolean;
  usedExchanges: Exchange[];
}

/**
 * What invalidates a loaded history. Declared here, next to the rest of the refresh policy, rather
 * than inline at the submit site — and consumed as a `staleAfter` edge, so nothing reaches into
 * history's status when data it derives from is purged. Prefix matching means a per-chain purge
 * (`purge:transactions:eth`) satisfies the `transactions` edge too.
 */
export const HISTORY_STALE_AFTER: readonly StaleAfterEdge[] = [
  { kind: ActivityKind.PURGE, parts: [Purgeable.TRANSACTIONS] },
  { kind: ActivityKind.PURGE, parts: [Purgeable.CENTRALIZED_EXCHANGES] },
];

interface ResolveOptions {
  chains: string[];
  fullRefresh: boolean;
  /** The caller's accounts as {@link resolveInputAccounts} left them, never the raw payload. */
  inputAccounts: ChainAddress[];
  usedExchanges: Exchange[];
  userInitiated: boolean;
  /** Whether history has been refreshed before; drives the sync-progress display. */
  everRefreshed: boolean;
}

interface UseHistoryRefreshPolicyReturn {
  detectNovelty: (accounts: ChainAddress[], usedExchanges: Exchange[]) => NoveltyDetection;
  filterSyncingExchanges: (exchanges: Exchange[] | undefined) => Exchange[];
  resolveInputAccounts: (accounts: ChainAddress[] | undefined, fullRefresh: boolean, chains: string[]) => ChainAddress[];
  resolveRefreshTargets: (
    payload: { exchanges?: Exchange[] },
    novelty: NoveltyDetection,
    opts: ResolveOptions,
  ) => RefreshTargets;
  shouldNotRefresh: (opts: { alreadyLoaded: boolean; novelty: NoveltyDetection }) => boolean;
}

/**
 * What a history refresh *should* cover: which accounts and exchanges are new, whether a refresh is
 * warranted at all, and what the resulting target set is. Split from the refresh itself so the
 * orchestration side owns only running the work.
 */
export function useHistoryRefreshPolicy(): UseHistoryRefreshPolicyReturn {
  const { isSameExchange, syncingExchanges } = useExchangeData();
  const { getAllAccounts } = useHistoryTransactionAccounts();
  const { filterAccounts } = useDisabledChains();
  const { isDecodableChains } = useSupportedChains();
  const { statusOf } = useNativeTask();

  /**
   * Novelty is "never attempted", which is what the old refreshed-keys set meant: it was written
   * when a refresh *started*, not when it succeeded. So this asks the completion ledger whether the
   * activity ever settled — in any outcome — rather than whether it ever succeeded.
   *
   * Keying this on `everCompleted` instead would leave a failed or cancelled sync novel forever,
   * and `resolveForFullRefresh` escalates any novelty into a full re-sync of every account.
   */
  function neverAttempted(kind: ActivityKind, ...parts: string[]): boolean {
    return statusOf(kind, ...parts).lastOutcome === undefined;
  }

  function filterSyncingExchanges(exchanges: Exchange[] | undefined): Exchange[] {
    return exchanges
      ? exchanges.filter(exchange => get(syncingExchanges).some(syncing => isSameExchange(syncing, exchange)))
      : get(syncingExchanges);
  }

  /**
   * The one door accounts enter this module through, so it is where the user's disabled chains are
   * removed. `getAllAccounts` filters its own; a caller-supplied list is filtered here.
   */
  function resolveInputAccounts(accounts: ChainAddress[] | undefined, fullRefresh: boolean, chains: string[]): ChainAddress[] {
    if (accounts?.length)
      return filterAccounts(accounts);
    if (fullRefresh)
      return getAllAccounts(chains);
    return [];
  }

  function detectNovelty(allAccounts: ChainAddress[], usedExchanges: Exchange[]): NoveltyDetection {
    return {
      newAccounts: allAccounts.filter(account => neverAttempted(ActivityKind.TX_SYNC, account.chain, account.address)),
      newExchanges: usedExchanges.filter(exchange => neverAttempted(ActivityKind.EXCHANGE_EVENTS, exchange.location, exchange.name)),
    };
  }

  function shouldNotRefresh({ alreadyLoaded, novelty }: { alreadyLoaded: boolean; novelty: NoveltyDetection }): boolean {
    return alreadyLoaded && novelty.newAccounts.length === 0 && novelty.newExchanges.length === 0;
  }

  /**
   * Resolves the accounts and exchanges a full refresh should cover.
   *
   * @remarks
   * `!everRefreshed` widens the scope and is not a duplicate of the entry guard: novelty means
   * "never attempted", so an account whose sync *failed* is not novel. Without it, a first load
   * where every account failed leaves every later background refresh with an empty account set,
   * and only a manual refresh recovers. Reaching here already means history has never loaded.
   */
  function resolveForFullRefresh(novelty: NoveltyDetection, chains: string[], opts: { userInitiated: boolean; everRefreshed: boolean }): { accounts: ChainAddress[]; exchanges: Exchange[] } {
    const wantsAllAccounts = novelty.newAccounts.length > 0 || opts.userInitiated || !opts.everRefreshed;
    return {
      accounts: wantsAllAccounts ? getAllAccounts(chains) : [],
      exchanges: get(syncingExchanges),
    };
  }

  function resolveForNovelItems(novelty: NoveltyDetection): { accounts: ChainAddress[]; exchanges: Exchange[] } {
    return {
      accounts: novelty.newAccounts.length > 0 ? novelty.newAccounts : [],
      exchanges: novelty.newExchanges.length > 0 ? novelty.newExchanges : [],
    };
  }

  function resolveRefreshTargets(
    payload: { exchanges?: Exchange[] },
    novelty: NoveltyDetection,
    opts: ResolveOptions,
  ): RefreshTargets {
    const { chains, everRefreshed, fullRefresh, inputAccounts, usedExchanges, userInitiated } = opts;
    const hasNovelty = novelty.newAccounts.length > 0 || novelty.newExchanges.length > 0;

    let resolved: { accounts: ChainAddress[]; exchanges: Exchange[] };

    if (fullRefresh)
      resolved = resolveForFullRefresh(novelty, chains, { everRefreshed, userInitiated });
    else if (hasNovelty)
      resolved = resolveForNovelItems(novelty);
    else
      resolved = { accounts: inputAccounts, exchanges: payload.exchanges ?? [] };

    const { accounts } = resolved;

    return {
      accounts,
      decodableAccounts: accounts.filter(account => isDecodableChains(account.chain)),
      exchanges: resolved.exchanges,
      fullRefresh,
      queryExchanges: fullRefresh || !!payload.exchanges,
      shouldShowSyncProgress: !everRefreshed || hasNovelty,
      usedExchanges,
    };
  }

  return {
    detectNovelty,
    filterSyncingExchanges,
    resolveInputAccounts,
    resolveRefreshTargets,
    shouldNotRefresh,
  };
}
