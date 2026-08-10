import type { RefreshTransactionsParams } from './types';
import { startPromise } from '@shared/utils';
import { err, type Result } from 'plainfp/result';
import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { logger } from '@/modules/core/common/logging/logging';
import { sigilBus } from '@/modules/core/sigil/event-bus';
import { combineOutcomes, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { historySyncFlow } from '@/modules/history/events/tx/history-sync.flow';
import { HISTORY_STALE_AFTER, type RefreshTargets, useHistoryRefreshPolicy } from '@/modules/history/events/tx/use-history-refresh-policy';
import { useHistoryTransactionAccounts } from '@/modules/history/events/tx/use-history-transaction-accounts';
import { useRefreshHandlers } from '@/modules/history/events/tx/use-refresh-handlers';
import { useTransactionSync } from '@/modules/history/events/tx/use-transaction-sync';
import { useUndecodedTransactionsStatus } from '@/modules/history/events/tx/use-undecoded-transactions-status';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { useEventsQueryStatusStore } from '@/modules/history/use-events-query-status-store';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { useSchedulerState } from '@/modules/session/use-scheduler-state';
import { UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseRefreshTransactionsReturn {
  refreshTransactions: (params?: RefreshTransactionsParams) => Promise<void>;
}

/**
 * Which wave of a sync a run is. `CONTINUATION` is the drained follow-up: it belongs to the sync
 * already on screen, so it adds to that progress rather than starting its own, and it does not
 * drain again (see {@link drainPending} for why one wave per run is the bound).
 */
const RefreshWave = {
  CONTINUATION: 'continuation',
  INITIAL: 'initial',
} as const;

type RefreshWave = (typeof RefreshWave)[keyof typeof RefreshWave];

export function useRefreshTransactions(): UseRefreshTransactionsReturn {
  let timeout: NodeJS.Timeout;

  const { initializeQueryStatus, resetQueryStatus, stopSyncing: stopTxSyncing } = useTxQueryStatusStore();
  const { initializeQueryStatus: initializeExchangeEventsQueryStatus, resetQueryStatus: resetExchangesQueryStatus, stopSyncing: stopEventsSyncing } = useEventsQueryStatusStore();
  const { filterDisabledChainAccounts } = useHistoryTransactionAccounts();
  const { statusOf, submitTask } = useNativeTask();
  const { fetchUndecodedTransactionsBreakdown } = useUndecodedTransactionsStatus();
  const { resetDecodingSyncProgress, resetUndecodedTransactionsStatus, resumeDecodingSyncProgress, stopDecodingSyncProgress } = useDecodingStatusStore();

  const { syncTransactionsByChains } = useTransactionSync();
  const {
    detectNovelty,
    filterSyncingExchanges,
    resolveInputAccounts,
    resolveRefreshTargets,
    shouldNotRefresh,
  } = useHistoryRefreshPolicy();
  const { pending: accountsPending } = useAccountLoadState();
  const { queryAllExchangeEvents, queryOnlineEvent, resetOnlineWarnings } = useRefreshHandlers();
  const { onHistoryFinished, onHistoryStarted } = useSchedulerState();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * A continuation carries only what the previous wave did not know about, so everything here that
   * clears state has to be skipped for it: the first wave's finished addresses and its online
   * warnings belong to the same sync, and wiping them is what made the progress bar restart with a
   * smaller denominator instead of growing.
   */
  function initializeRefresh(targets: RefreshTargets, wave: RefreshWave): void {
    const continuation = wave === RefreshWave.CONTINUATION;

    if (!continuation) {
      resetQueryStatus();
      resetOnlineWarnings();
    }

    if (!(targets.accounts.length > 0 || targets.exchanges.length > 0)) {
      return;
    }

    onHistoryStarted();

    if (!(targets.accounts.length > 0 && targets.shouldShowSyncProgress)) {
      return;
    }

    initializeQueryStatus(targets.decodableAccounts, { extend: continuation });

    if (continuation) {
      // ⚠️ Re-arm, do not reset. The decode section is gated by a single flag that the previous
      // wave's `finally` turned off, so skipping this entirely would drop every decode message this
      // wave produces and leave the section reading complete over the previous wave's rows.
      resumeDecodingSyncProgress();
      return;
    }

    resetUndecodedTransactionsStatus();
    resetDecodingSyncProgress();
  }

  function resolveOnlineQueries(
    targets: RefreshTargets,
    disableEvmEvents: boolean,
    queries: OnlineHistoryEventsQueryType[] | undefined,
  ): OnlineHistoryEventsQueryType[] {
    if (targets.fullRefresh || disableEvmEvents)
      return [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS, OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS];
    return queries ?? [];
  }

  /** Same continuation rule as {@link initializeRefresh}, for the exchange half of the panel. */
  function seedExchangeProgress(targets: RefreshTargets, wave: RefreshWave): void {
    const continuation = wave === RefreshWave.CONTINUATION;

    if (!continuation)
      resetExchangesQueryStatus();

    if (targets.queryExchanges && targets.shouldShowSyncProgress)
      initializeExchangeEventsQueryStatus(targets.usedExchanges, { extend: continuation });
  }

  async function executeOperations(
    targets: RefreshTargets,
    disableEvmEvents: boolean,
    queries: OnlineHistoryEventsQueryType[] | undefined,
    umbrella: ActivityId,
    wave: RefreshWave,
  ): Promise<Result<void, TaskError>> {
    if (targets.fullRefresh || targets.decodableAccounts.length > 0)
      await fetchUndecodedTransactionsBreakdown();

    seedExchangeProgress(targets, wave);

    // The shape of the refresh comes off the declaration rather than being rebuilt here, so what a
    // test asserts about `historySyncFlow` is what actually runs. Everything is a child of the
    // umbrella — exchanges and online queries used to be submitted without a parent, which left
    // them outside the tree and outside the umbrella's derived progress.
    const children = historySyncFlow.children({
      accounts: targets.accounts,
      exchanges: targets.queryExchanges ? targets.usedExchanges : [],
      queries: resolveOnlineQueries(targets, disableEvmEvents, queries),
    });

    const exchanges = children.flatMap(child => child.payload.type === 'exchange' ? [child.payload.exchange] : []);

    // ⚠️ Two of the three kinds are dispatched as a batch rather than per declared child, because
    // each owns a fan-out *shape* the declaration cannot express: chains group their accounts onto
    // per-chain lanes and hand off to a decode, and exchanges run one location's accounts in
    // sequence with two locations at a time. Driving those per child would silently discard both.
    // The declaration still names every child, and names them with the same id constructors the
    // producers submit under, so the tree and the umbrella's progress stay accurate.
    const asyncOperations: Promise<Result<void, TaskError>[]>[] = [
      ...(targets.accounts.length > 0
        ? [syncTransactionsByChains(targets.accounts, targets.shouldShowSyncProgress, umbrella)]
        : []),
      ...(exchanges.length > 0 ? [queryAllExchangeEvents(exchanges, umbrella)] : []),
      ...children.flatMap(child => child.payload.type === 'online'
        ? [queryOnlineEvent(child.payload.query, umbrella).then(outcome => [outcome])]
        : []),
    ];

    // Collected, not discarded: the umbrella settles on these, and a run whose every child failed
    // must not write the completion that `alreadyLoaded` reads.
    const outcomes: Result<void, TaskError>[] = [];

    for (const operation of asyncOperations) {
      try {
        outcomes.push(...await operation);
      }
      catch (error: unknown) {
        logger.error(error);
        // The thrown value rides along as `cause`; the operation itself is what failed, and each
        // producer has already logged its own detail.
        outcomes.push(err(TaskFailed({ cause: error, message: 'a refresh operation threw' })));
      }
    }

    // One read, not two. This was queued twice under two identifiers on a cap-1 queue — the second
    // through a `fetchUndecodedTransactionsStatus` alias that only ever called this — so the cap
    // serialised them into the same backend read twice, the second slipping past the in-flight
    // guard precisely because the first had finished. Not awaited: the refresh is over and the
    // count is a display concern. Re-entry is the activity's own to dedup.
    startPromise(fetchUndecodedTransactionsBreakdown());

    return combineOutcomes(outcomes);
  }

  /**
   * Pick up whatever was added while this refresh was running.
   *
   * There is no pending set any more: an account added mid-refresh has never been attempted, and
   * "never attempted" is exactly what the completion ledger answers. So the drain is the same
   * novelty question asked once more, after the umbrella settles.
   *
   * ⚠️ Passes the novel items as an explicit payload rather than re-entering as a full refresh.
   * A full refresh escalates any novelty into `getAllAccounts`, so draining that way would re-sync
   * every account instead of the handful that arrived late.
   *
   * ⚠️ The delay is not cosmetic: `submitTask` resolves a tick before the record settles, so an
   * immediate re-entry would read the umbrella as still active and take the early return, dropping
   * the drain entirely.
   *
   * ⚠️ The drained run does not drain again. Asking the ledger is a *derived* question, unlike the
   * old pending set which emptied as it was consumed — so without a bound, any account that never
   * gets a `TX_SYNC` activity would read as novel forever and re-trigger a refresh every 100ms.
   * One wave per run; a later arrival waits for the next refresh.
   */
  function drainPending(params: RefreshTransactionsParams): void {
    const { chains = [] } = params;
    // Disabled chains are filtered before the novelty question, never after — an account the backend
    // silently skips would otherwise read as novel forever and drain on every refresh.
    const accounts = filterDisabledChainAccounts(resolveInputAccounts(undefined, true, chains));
    const { newAccounts, newExchanges } = detectNovelty(accounts, filterSyncingExchanges(undefined));

    if (newAccounts.length === 0 && newExchanges.length === 0)
      return;

    timeout = setTimeout(() => {
      startPromise(refreshOnce({
        ...params,
        payload: {
          ...params.payload,
          accounts: newAccounts.length > 0 ? newAccounts : undefined,
          exchanges: newExchanges.length > 0 ? newExchanges : undefined,
        },
      }, RefreshWave.CONTINUATION));
    }, 100);
  }

  async function refreshOnce(params: RefreshTransactionsParams, wave: RefreshWave): Promise<void> {
    const { chains = [], disableEvmEvents = false, payload = {}, userInitiated = false } = params;
    const fullRefresh = Object.keys(payload).length === 0;

    // The scope below is a snapshot of the account store, and the store is filled one chain at a
    // time. Taking it mid-read drops whatever has not arrived, and the sync then reports complete
    // over a scope that never covered those chains. Guarded rather than awaited unconditionally, so
    // the common idle path keeps its current ordering.
    const accountRead = accountsPending();
    if (accountRead)
      await accountRead;

    const usedExchanges = filterSyncingExchanges(payload.exchanges);
    // Filter before novelty detection so disabled-chain accounts are not flagged as newly
    // added and queued as pending refreshes that the backend would silently skip.
    const allCurrentAccounts = filterDisabledChainAccounts(
      resolveInputAccounts(payload.accounts, fullRefresh, chains),
    );
    const novelty = detectNovelty(allCurrentAccounts, usedExchanges);

    const status = statusOf(ActivityKind.HISTORY_SYNC);
    if (shouldNotRefresh({ alreadyLoaded: status.everCompleted && !userInitiated, novelty }))
      return;

    // Outside the activity on purpose: `submitTask` dedups by id, so a second caller would be handed
    // the in-flight promise and this would never run. Nothing needs recording here — whatever this
    // caller brought is still unattempted when the running umbrella settles, and `drainPending`
    // asks the ledger for exactly that.
    if (status.active)
      return;

    const targets = resolveRefreshTargets(payload, novelty, {
      chains,
      everRefreshed: status.everCompleted,
      fullRefresh,
      usedExchanges,
      userInitiated,
    });

    const umbrellaId = makeActivityId(ActivityKind.HISTORY_SYNC);

    // One umbrella for the whole refresh: its liveness is the re-entrancy guard above, its freshness
    // answers "has history ever loaded", and every chain, exchange and decode runs as its child.
    await submitTask({
      id: umbrellaId,
      kind: ActivityKind.HISTORY_SYNC,
      lane: UMBRELLA_LANE,
      rerunnable: false,
      staleAfter: HISTORY_STALE_AFTER,
      // 🔴 The outcome is the children's, not a foregone `ok`. This umbrella *is* the subject for
      // its kind — `alreadyLoaded` below reads its `everCompleted` — so returning success
      // unconditionally meant an all-failed first sync (backend unreachable at login, every chain
      // fails) still wrote "history has loaded", and every later non-user-initiated refresh
      // short-circuited on it: history silently never synced again for the session. It cannot be a
      // `container` for the same reason — the entry is needed, it just has to be true. A run that
      // targeted nothing settles SKIPPED for the same reason, which is what stops a refresh fired
      // before any account has loaded from claiming the whole history.
      run: async (): Promise<Result<void, TaskError>> => {
        initializeRefresh(targets, wave);

        try {
          return await executeOperations(targets, disableEvmEvents, payload.queries, umbrellaId, wave);
        }
        catch (error) {
          logger.error(error);
          return err(TaskFailed({ cause: error, message: 'the history refresh threw' }));
        }
        finally {
          onHistoryFinished();
          stopTxSyncing();
          stopEventsSyncing();
          stopDecodingSyncProgress();
          sigilBus.emit('history:ready');
        }
      },
      title: t('task_center.group.history_sync'),
    });

    if (wave === RefreshWave.INITIAL)
      drainPending(params);
  }

  async function refreshTransactions(params: RefreshTransactionsParams = {}): Promise<void> {
    await refreshOnce(params, RefreshWave.INITIAL);
  }

  onScopeDispose(() => {
    if (timeout)
      clearTimeout(timeout);
  });

  return {
    refreshTransactions,
  };
}
