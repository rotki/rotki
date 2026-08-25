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
  const { getTransactionTypeFromChain } = useHistoryTransactionAccounts();
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

    initializeQueryStatus(
      targets.accounts.map(account => ({ ...account, subtype: getTransactionTypeFromChain(account.chain) })),
      { extend: continuation },
    );

    if (continuation) {
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

  /**
   * Dispatches every half of a refresh — chains, exchanges and online queries — and reduces them to
   * the umbrella's single verdict.
   *
   * @remarks
   * Chains and exchanges dispatch as a batch rather than per declared child, because each owns a
   * fan-out shape the declaration cannot express: chains group accounts onto per-chain lanes then
   * hand off to a decode, exchanges run one location's accounts in sequence. Driving those per child
   * silently discards both. The declaration still names every child with the same id constructors
   * the producers submit under, so the tree and progress stay accurate.
   *
   * @returns the **account half's** verdict alone. Nothing else may vote: fold all three kinds
   * together and a protocol query that happened to succeed records the completion over a run where
   * every chain failed. Nor may it require every kind to succeed — an online source failing is
   * ordinary, a missing key or an unauthenticated integration, and failing the umbrella on that
   * re-syncs history forever. The entry answers one question, "has the account history loaded".
   */
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

    const children = historySyncFlow.children({
      accounts: targets.accounts,
      exchanges: targets.queryExchanges ? targets.usedExchanges : [],
      queries: resolveOnlineQueries(targets, disableEvmEvents, queries),
    });

    const exchanges = children.flatMap(child => child.payload.type === 'exchange' ? [child.payload.exchange] : []);

    const asyncOperations: { accounts: boolean; work: Promise<Result<void, TaskError>[]> }[] = [
      ...(targets.accounts.length > 0
        ? [{ accounts: true, work: syncTransactionsByChains(targets.accounts, targets.shouldShowSyncProgress, umbrella) }]
        : []),
      ...(exchanges.length > 0 ? [{ accounts: false, work: queryAllExchangeEvents(exchanges, umbrella) }] : []),
      ...children.flatMap(child => child.payload.type === 'online'
        ? [{ accounts: false, work: queryOnlineEvent(child.payload.query, umbrella).then(outcome => [outcome]) }]
        : []),
    ];

    const accountOutcomes: Result<void, TaskError>[] = [];
    const otherOutcomes: Result<void, TaskError>[] = [];

    for (const operation of asyncOperations) {
      const sink = operation.accounts ? accountOutcomes : otherOutcomes;
      try {
        sink.push(...await operation.work);
      }
      catch (error: unknown) {
        logger.error(error);
        sink.push(err(TaskFailed({ cause: error, message: 'a refresh operation threw' })));
      }
    }

    startPromise(fetchUndecodedTransactionsBreakdown());

    return accountOutcomes.length > 0
      ? combineOutcomes(accountOutcomes)
      : combineOutcomes(otherOutcomes);
  }

  /**
   * Pick up whatever was added while this refresh was running.
   *
   * An account added mid-refresh has never been attempted, which is what the completion ledger
   * answers, so the drain is the same novelty question asked again once the umbrella settles.
   *
   * Three things it must keep doing:
   * - Pass the novel items as an explicit payload. A full refresh escalates novelty into
   *   `getAllAccounts` and would re-sync every account instead of the few that arrived late.
   * - Keep the delay. `submitTask` resolves a tick before the record settles, so immediate re-entry
   *   reads the umbrella as active and takes the early return, dropping the drain.
   * - Drain once per run. The ledger is a *derived* question, so an account that never gets a
   *   `TX_SYNC` activity reads as novel forever and would re-trigger every 100ms.
   */
  function drainPending(params: RefreshTransactionsParams): void {
    const { chains = [] } = params;
    const accounts = resolveInputAccounts(undefined, true, chains);
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

  /**
   * One wave of a refresh, as a single HISTORY_SYNC umbrella parenting every chain, exchange and
   * decode it fans out into.
   *
   * @remarks
   * The umbrella's liveness is the re-entrancy guard and its freshness answers "has history ever
   * loaded", which is why it takes its outcome from the children rather than returning a foregone
   * `ok`.
   *
   * An unconditional success lets an all-failed first sync record "history has loaded", and every
   * later refresh then short-circuits on it. For the same reason it cannot be a `container`: the
   * ledger entry is needed, it just has to be true. A run that targeted nothing settles SKIPPED,
   * which stops a refresh fired before any account loaded from claiming the whole history.
   */
  async function refreshOnce(params: RefreshTransactionsParams, wave: RefreshWave): Promise<void> {
    const { chains = [], disableEvmEvents = false, payload = {}, userInitiated = false } = params;
    const fullRefresh = Object.keys(payload).length === 0;

    const accountRead = accountsPending();
    if (accountRead)
      await accountRead;

    const usedExchanges = filterSyncingExchanges(payload.exchanges);
    const allCurrentAccounts = resolveInputAccounts(payload.accounts, fullRefresh, chains);
    const novelty = detectNovelty(allCurrentAccounts, usedExchanges);

    const status = statusOf(ActivityKind.HISTORY_SYNC);
    if (shouldNotRefresh({ alreadyLoaded: status.everCompleted && !userInitiated, novelty }))
      return;

    // Must stay outside the activity: `submitTask` dedups by id, so moving it in hands the second
    // caller the in-flight promise and the check never runs.
    if (status.active)
      return;

    const targets = resolveRefreshTargets(payload, novelty, {
      chains,
      everRefreshed: status.everCompleted,
      fullRefresh,
      inputAccounts: allCurrentAccounts,
      usedExchanges,
      userInitiated,
    });

    const umbrellaId = makeActivityId(ActivityKind.HISTORY_SYNC);

    await submitTask({
      id: umbrellaId,
      kind: ActivityKind.HISTORY_SYNC,
      lane: UMBRELLA_LANE,
      rerunnable: false,
      staleAfter: HISTORY_STALE_AFTER,
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
