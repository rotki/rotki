import type { BlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import { err, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { arrayify } from '@/modules/core/common/data/array';
import { setDigest } from '@/modules/core/common/data/digest';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { Cancelled, Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { BALANCES_LANE, DEFAULT_PRIORITY, Priority } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useActivityBatch } from '@/modules/task-center/use-activity-batch';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useBalanceProcessingService } from './services/use-balance-processing-service';

interface RefreshOptions {
  /**
   * Run token detection before the network query. A flow parameter, not a property of the chain:
   * the same chain detects on a login refresh and does not on a periodic one.
   */
  readonly detect?: boolean;
  /**
   * Narrow the detection stage to these addresses. Ignored without `detect`, and omitted it covers
   * every address on the chain — an account addition is the one flow that knows a smaller answer.
   */
  readonly detectAddresses?: string[];
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
 * Its body is **statement order, not `deps`**: detect, then query. The query must see what
 * detection found, and that is a sequence inside one activity rather than two activities with an
 * edge between them — which is what let a chain's detection and its balance query drift apart into
 * separate top-level rows with nothing tying them together.
 *
 * Detection is the only genuinely per-address stage. The accounts read is one call per chain and
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
  const { isAddressExcluded, isChainExcluded } = useDisabledChains();

  /**
   * Whether a *network* refresh is already running for this chain.
   *
   * It does not wait on the chain's hydration from the DB, and must not: the two layers overlap
   * by design. A cached read landing after a network result would overwrite fresh balances with
   * stale ones, which balance writes being monotonic prevents outright — the older payload is
   * discarded whichever order the two land in. Two mechanisms for one hazard, and the cheaper one
   * wins.
   *
   * Read by the `periodic` branch only. It is not redundant with `submitTask`'s id dedup: dedup
   * covers a run that is *submitted*, this covers the window where the POST itself is in flight.
   */
  const isChainRefreshing = (chain: string): boolean => get(refreshState.refreshingChains).has(chain);

  /**
   * Refreshes blockchain balances from the network, as one BLOCKCHAIN_BALANCES activity per chain
   * under a single umbrella.
   *
   * @remarks
   * Chains run on `BALANCES_LANE` at cap 2, and a background run pauses while a history sync holds
   * the orchestrator. A `USER` refresh supersedes the run in flight rather than joining it, and
   * jumps queued background work.
   *
   * The umbrella's identity is scope + mode, so two identical runs dedup onto one while a full
   * refresh and a single-chain one coexist. Its scope comes from `/blockchains/supported`, which
   * lands before the account walk, so the denominator is honest from the first render — it must
   * never read a store that is still filling.
   *
   * @param payload - what to refresh; an empty `addresses` list means every address, the same as
   * omitting it
   * @param mode - `USER` supersedes and jumps the queue, `PERIODIC` yields to a chain already
   * refreshing, `BACKGROUND` neither
   * @param options - `detect` runs token detection before the query, narrowed to `detectAddresses`
   * when given
   */
  const refreshBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
    mode: RefreshMode = RefreshMode.BACKGROUND,
    options: RefreshOptions = {},
  ): Promise<void> => {
    const { detect = false, detectAddresses } = options;
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    const requestedAddresses = addresses?.length ? addresses : undefined;

    /** Addresses of `chain` `disabledChainQueries` still allows, or `undefined` for the whole chain. */
    const allowedAddresses = (chain: string): string[] | undefined =>
      requestedAddresses?.filter(address => !isAddressExcluded(chain, address));

    const submit = mode === RefreshMode.USER ? supersedeTask : submitTask;

    /**
     * One chain's refresh: token detection when asked, then the network query.
     *
     * @remarks
     * `detect` and the address narrowing are both part of the activity id, because `submitTask`
     * dedups by it. Share an id and a login sweep joins an in-flight background refresh, or a second
     * addition joins the first, and detection for those addresses silently never happens —
     * `withDetection` still writes `lastAutoDetectAt`, so the cooldown suppresses the next sweep too.
     *
     * Those parts are *appended*, never substituted: every reader is prefix-based, so the kind
     * and the chain have to stay leading.
     *
     * The body runs in statement order, and that order is the contract: an excluded chain is
     * answered before detection so it costs neither a detect nor a query, detection is awaited so
     * the query sees the tokens it found, and cancellation is re-checked afterwards because
     * cancelling the children cannot stop this body. Each of those exits settles SKIPPED or
     * CANCELLED rather than `ok`, so nothing records a completion for work that did not run.
     */
    const chainJob = async (chain: string, parent: ActivityId | undefined): Promise<void> => {
      const chainAddresses = allowedAddresses(chain);
      const chainPayload = { addresses: chainAddresses ?? addresses, blockchain: chain, isXpub };
      const id = detect
        ? makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain, ActivityPart.DETECT, ...(detectAddresses?.length ? [setDigest(detectAddresses)] : []))
        : makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, chain);
      await submit({
        id,
        parent,
        kind: ActivityKind.BLOCKCHAIN_BALANCES,
        lane: BALANCES_LANE,
        priority: mode === RefreshMode.USER ? Priority.USER : DEFAULT_PRIORITY,
        rerunnable: true,
        run: async ({ cancelled, runTask }): Promise<Result<void, TaskError>> => {
          // A dropped refresh settles SKIPPED, never `ok`.
          if (mode === RefreshMode.PERIODIC && isChainRefreshing(chain))
            return err(Skipped({ message: t('actions.balances.blockchain.skipped.busy') }));

          // Empty `chainAddresses` means every named address is excluded; naming none leaves it
          // `undefined`.
          if (isChainExcluded(chain) || chainAddresses?.length === 0)
            return err(Skipped({ message: t('actions.balances.blockchain.skipped.disabled') }));

          if (detect)
            await detectForChain(chain, id, detectAddresses);

          // Cancelled children settle, so the await above resolves either way.
          if (cancelled())
            return err(Cancelled({ message: t('actions.balances.blockchain.cancelled') }));

          return handleRefresh(runTask, chainPayload);
        },
        // Stage-neutral: fixed at submit time, while this job has two stages.
        subtitle: activityLabelFor(msg.$t('task_center.activity.blockchain_balances.chain'), { chain: getChainName(chain) }),
        title: t('task_center.group.blockchain_balances'),
      });
    };

    await runActivityBatch(
      {
        id: makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, ActivityPart.RUN, setDigest(chains), mode),
        // The chains are the subjects; this only contains them, so it records no completion.
        container: true,
        kind: ActivityKind.BLOCKCHAIN_BALANCES,
        subtitle: activityLabelFor(msg.$t('task_center.activity.blockchain_balances.run'), { count: chains.length }),
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
