import type { BlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import { err, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { arrayify } from '@/modules/core/common/data/array';
import { setDigest } from '@/modules/core/common/data/digest';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { BALANCES_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useActivityBatch } from '@/modules/task-center/use-activity-batch';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useBalanceProcessingService } from './services/use-balance-processing-service';

/**
 * Who asked for this refresh, which is what decides what happens when the chain is already busy.
 *
 * - `background`: join the run in flight. Two callers wanting the same thing share one query.
 * - `periodic`: settle SKIPPED with a reason. A tick that finds the chain busy has nothing to add,
 *   and recording it as `ok` would mark the chain refreshed when nothing ran.
 * - `user`: supersede. Someone pressed refresh, so they get a fresh query with *their* parameters
 *   rather than whatever the background run happened to be doing.
 */
export type RefreshMode = 'background' | 'periodic' | 'user';

export interface RefreshOptions {
  /**
   * Run token detection before the network query. Per §6 this is a flow parameter, not a property
   * of the chain: the same chain detects on a login refresh and does not on a periodic one.
   */
  readonly detect?: boolean;
}

interface UseBlockchainBalancesReturn {
  refreshBlockchainBalances: (payload?: BlockchainBalancePayload, mode?: RefreshMode, options?: RefreshOptions) => Promise<void>;
}

/**
 * Layer 2 — the work, as **one chain job per chain**.
 *
 * The chain is the unit of identity, ordering and exclusion, and the job is a *parent*, not a leaf:
 *
 * ```
 * chain job                 ← identity = chain
 *   └─ per-address children ← only where the work is genuinely per-address (detection)
 * ```
 *
 * ⭐ Its body is **statement order, not `deps`**: detect, then query. The query must see what
 * detection found, and that is a sequence inside one activity rather than two activities with an
 * edge between them — which is what let a chain's detection and its balance query drift apart into
 * separate top-level rows with nothing tying them together.
 *
 * ⭐ Detection is the only genuinely per-address stage. The accounts read is one call per chain and
 * so is the balance query, so neither earns children.
 *
 * Reading a chain's balances back out of the user's own database is the *other* layer and lives in
 * {@link useBalanceHydration} — it is not work, so it is not here.
 */
export function useBlockchainBalances(): UseBlockchainBalancesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName, supportedChains } = useSupportedChains();

  const { handleRefresh } = useBalanceProcessingService();
  const { detectForChain } = useTokenDetectionOrchestrator();
  const { runActivityBatch } = useActivityBatch();
  const { submitTask, supersedeTask } = useNativeTask();
  const refreshState = useBalanceRefreshState();

  /**
   * Whether a *network* refresh is already running for this chain.
   *
   * ⭐ It does not wait on the chain's hydration from the DB, and must not: the two layers overlap
   * by design. A cached read landing after a network result would overwrite fresh balances with
   * stale ones, which balance writes being monotonic prevents outright — the older payload is
   * discarded whichever order the two land in. Two mechanisms for one hazard, and the cheaper one
   * wins.
   *
   * ⚠️ Read by the `periodic` branch only. It is not redundant with `submitTask`'s id dedup: dedup
   * covers a run that is *submitted*, this covers the window where the POST itself is in flight.
   */
  const isChainRefreshing = (chain: string): boolean => get(refreshState.refreshingChains).has(chain);

  // Network refresh — one native BLOCKCHAIN_BALANCES activity per chain on BALANCES_LANE (cap 2,
  // paused during decode by the orchestrator rule, replacing the old BalanceQueueService).
  const refreshBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
    mode: RefreshMode = 'background',
    options: RefreshOptions = {},
  ): Promise<void> => {
    const { detect = false } = options;
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    // ⭐ A user-initiated refresh replaces the run in flight instead of joining it. `supersedeTask`
    // is the single shared helper for that — cancel, *await the cancelled promise*, then submit —
    // because `finish()` is what frees the id, and resubmitting before it dedups onto the corpse.
    //
    // This is what retired the old `until(() => isChainRefreshing(chain)).toBe(false)` poll on the
    // non-periodic path. That poll was standing in for supersede: it made a manual refresh wait for
    // the background run to finish and then re-query, which is the right *outcome* reached by
    // waiting out work the user had already superseded.
    const submit = mode === 'user' ? supersedeTask : submitTask;

    const chainJob = async (chain: string, parent: ActivityId | undefined): Promise<void> => {
      const chainPayload = { addresses, blockchain: chain, isXpub };
      const id = makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain);
      await submit({
        id,
        parent,
        kind: ActivityKind.BLOCKCHAIN_BALANCES,
        lane: BALANCES_LANE,
        rerunnable: true,
        run: async ({ runTask }): Promise<Result<void, TaskError>> => {
          // 🔴 A dropped refresh is SKIPPED with a reason, never `ok`. Returning success here
          // recorded a completion for work that never ran, so the ledger — and `everCompleted`
          // with it — reported this chain as refreshed. Same class as a green "Sync Complete"
          // over chains that were never synced.
          //
          // `Skipped` is not `isActionable`, so this raises no notification; it settles the
          // activity terminal-but-not-successful and the task centre renders the reason.
          if (mode === 'periodic' && isChainRefreshing(chain))
            return err(Skipped({ message: t('actions.balances.blockchain.skipped.busy') }));

          // ⭐ Statement order is the ordering. Detection's children run under this job and are
          // awaited here, so the query below sees the tokens they found — no `deps` edge, no
          // second top-level activity, and cancelling this chain now stops the addresses too.
          if (detect)
            await detectForChain(chain, id);

          return handleRefresh(runTask, chainPayload);
        },
        subtitle: activityLabelFor(msg.$t('task_center.activity.blockchain_balances.query'), { chain: getChainName(chain) }),
        title: t('task_center.group.blockchain_balances'),
      });
    };

    // ⭐ §5. The run is the fan-out, and its identity is **scope + mode**: two identical runs dedup
    // onto one umbrella, while a full refresh and a single-chain one coexist because their scopes
    // differ. `runActivityBatch` declares the children before the umbrella's body awaits them, and
    // suppresses the umbrella entirely for a single chain — a parent over one child is a second row
    // describing the same work.
    //
    // ⚠️ Scope is taken from `/blockchains/supported`, which lands before the account walk, so the
    // denominator is honest from the first render. It must never be a function of a store that is
    // still filling: that is what silently dropped chains from the history sync.
    await runActivityBatch(
      {
        id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, ActivityPart.RUN, setDigest(chains), mode),
        kind: ActivityKind.BLOCKCHAIN_BALANCES,
        title: t('task_center.group.blockchain_balances'),
      },
      chains,
      async (chain, parent) => chainJob(chain, parent),
    );
  };

  return {
    refreshBlockchainBalances,
  };
}
