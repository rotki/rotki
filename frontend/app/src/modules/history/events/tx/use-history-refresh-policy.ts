import type { Exchange } from '@/modules/balances/types/exchanges';
import type { BankConnectionIdentity } from '@/modules/banks/types';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import type { StaleAfterEdge } from '@/modules/task-center/core/orchestrator/spec';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { accountSyncActivity, bankEventsActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { useHistoryTransactionAccounts } from '@/modules/history/events/tx/use-history-transaction-accounts';
import { Purgeable } from '@/modules/session/purge';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface NoveltyDetection {
  newAccounts: ChainAddress[];
  newExchanges: Exchange[];
  newBanks: BankConnectionIdentity[];
}

export interface RefreshTargets {
  accounts: ChainAddress[];
  banks: BankConnectionIdentity[];
  decodableAccounts: ChainAddress[];
  exchanges: Exchange[];
  fullRefresh: boolean;
  queryBanks: boolean;
  queryExchanges: boolean;
  shouldShowSyncProgress: boolean;
  usedBanks: BankConnectionIdentity[];
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

interface ResolvedTargets {
  accounts: ChainAddress[];
  banks: BankConnectionIdentity[];
  exchanges: Exchange[];
}

interface ResolveOptions {
  chains: string[];
  fullRefresh: boolean;
  /** The caller's accounts as {@link resolveInputAccounts} left them, never the raw payload. */
  inputAccounts: ChainAddress[];
  usedBanks: BankConnectionIdentity[];
  usedExchanges: Exchange[];
  userInitiated: boolean;
  /** Whether history has been refreshed before; drives the sync-progress display. */
  everRefreshed: boolean;
}

interface UseHistoryRefreshPolicyReturn {
  detectNovelty: (accounts: ChainAddress[], usedExchanges: Exchange[], usedBanks: BankConnectionIdentity[]) => NoveltyDetection;
  filterSyncingBanks: (banks: BankConnectionIdentity[] | undefined) => BankConnectionIdentity[];
  filterSyncingExchanges: (exchanges: Exchange[] | undefined) => Exchange[];
  resolveInputAccounts: (accounts: ChainAddress[] | undefined, fullRefresh: boolean, chains: string[]) => ChainAddress[];
  resolveRefreshTargets: (
    payload: { banks?: BankConnectionIdentity[]; exchanges?: Exchange[] },
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
  const { connections: bankConnections } = storeToRefs(useBankConnectionsStore());
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
  function neverAttempted(kind: ActivityKind, ...parts: (string | number)[]): boolean {
    return statusOf(kind, ...parts).lastOutcome === undefined;
  }

  const connectedBanks = (): BankConnectionIdentity[] =>
    get(bankConnections).map(({ location, name }) => ({ location, name }));

  /** Every bank connection syncs; there is no per-connection opt-out as there is for exchanges. */
  function filterSyncingBanks(banks: BankConnectionIdentity[] | undefined): BankConnectionIdentity[] {
    const connected = connectedBanks();
    return banks
      ? banks.filter(bank => connected.some(candidate => isSameExchange(candidate, bank)))
      : connected;
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

  function detectNovelty(allAccounts: ChainAddress[], usedExchanges: Exchange[], usedBanks: BankConnectionIdentity[]): NoveltyDetection {
    return {
      newAccounts: allAccounts.filter(account =>
        neverAttempted(accountSyncActivity.kind, ...accountSyncActivity.partsOf(account))),
      newBanks: usedBanks.filter(bank =>
        neverAttempted(bankEventsActivity.kind, ...bankEventsActivity.partsOf(bank))),
      newExchanges: usedExchanges.filter(exchange =>
        neverAttempted(exchangeEventsActivity.kind, ...exchangeEventsActivity.partsOf(exchange))),
    };
  }

  function shouldNotRefresh({ alreadyLoaded, novelty }: { alreadyLoaded: boolean; novelty: NoveltyDetection }): boolean {
    return alreadyLoaded && novelty.newAccounts.length === 0 && novelty.newExchanges.length === 0 && novelty.newBanks.length === 0;
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
  function resolveForFullRefresh(novelty: NoveltyDetection, chains: string[], opts: { userInitiated: boolean; everRefreshed: boolean }): ResolvedTargets {
    const wantsAllAccounts = novelty.newAccounts.length > 0 || opts.userInitiated || !opts.everRefreshed;
    return {
      accounts: wantsAllAccounts ? getAllAccounts(chains) : [],
      banks: connectedBanks(),
      exchanges: get(syncingExchanges),
    };
  }

  function resolveForNovelItems(novelty: NoveltyDetection): ResolvedTargets {
    return {
      accounts: novelty.newAccounts.length > 0 ? novelty.newAccounts : [],
      banks: novelty.newBanks.length > 0 ? novelty.newBanks : [],
      exchanges: novelty.newExchanges.length > 0 ? novelty.newExchanges : [],
    };
  }

  function resolveRefreshTargets(
    payload: { banks?: BankConnectionIdentity[]; exchanges?: Exchange[] },
    novelty: NoveltyDetection,
    opts: ResolveOptions,
  ): RefreshTargets {
    const { chains, everRefreshed, fullRefresh, inputAccounts, usedBanks, usedExchanges, userInitiated } = opts;
    const hasNovelty = novelty.newAccounts.length > 0 || novelty.newExchanges.length > 0 || novelty.newBanks.length > 0;

    let resolved: ResolvedTargets;

    if (fullRefresh)
      resolved = resolveForFullRefresh(novelty, chains, { everRefreshed, userInitiated });
    else if (hasNovelty)
      resolved = resolveForNovelItems(novelty);
    else
      resolved = { accounts: inputAccounts, banks: payload.banks ?? [], exchanges: payload.exchanges ?? [] };

    const { accounts } = resolved;

    return {
      accounts,
      banks: resolved.banks,
      decodableAccounts: accounts.filter(account => isDecodableChains(account.chain)),
      exchanges: resolved.exchanges,
      fullRefresh,
      queryBanks: fullRefresh || !!payload.banks,
      queryExchanges: fullRefresh || !!payload.exchanges,
      shouldShowSyncProgress: !everRefreshed || hasNovelty,
      usedBanks,
      usedExchanges,
    };
  }

  return {
    detectNovelty,
    filterSyncingBanks,
    filterSyncingExchanges,
    resolveInputAccounts,
    resolveRefreshTargets,
    shouldNotRefresh,
  };
}
