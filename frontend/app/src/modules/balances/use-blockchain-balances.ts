import type { BlockchainBalancePayload } from '@/modules/balances/types/blockchain-balances';
import type { ActivityId } from '@/modules/task-center/core/types';
import { err, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { balancesRunActivity, chainBalancesActivity } from '@/modules/balances/balances.activity';
import { useTokenDetectionOrchestrator } from '@/modules/balances/blockchain/use-token-detection-orchestrator';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { arrayify } from '@/modules/core/common/data/array';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { Cancelled, Skipped, type TaskError } from '@/modules/core/tasks/task-result';
import { useDisabledChains } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chains';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { DEFAULT_PRIORITY, Priority } from '@/modules/task-center/core/orchestrator/spec';
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
  /**
   * Work to declare with the chains and run after them, as part of the same refresh: it is handed
   * the chain jobs' ids to depend on and the parent to submit under. See `runActivityBatch`.
   */
  readonly followUp?: (chainIds: ActivityId[], parent: ActivityId | undefined) => Promise<unknown>;
}

interface UseBlockchainBalancesReturn {
  refreshBlockchainBalances: (payload?: BlockchainBalancePayload, mode?: RefreshMode, options?: RefreshOptions) => Promise<void>;
}

/**
 * The scheduling priority of a refresh, shared by its umbrella and its chain jobs: a chain cannot
 * start before its umbrella, so an umbrella at a lower priority would hold a user's refresh back.
 */
function refreshPriority(userStarted: boolean): Priority {
  return userStarted ? Priority.USER : DEFAULT_PRIORITY;
}

function accountRunRevision(chains: string[], revisions: Record<string, number>): string | undefined {
  return chains.some(chain => revisions[chain] > 0)
    ? chains.map(chain => `${chain}:${revisions[chain]}`).join(',')
    : undefined;
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
  const { getAccounts, revisionOf } = useBlockchainAccountsStore();
  const { isAddressExcluded, isChainExcluded } = useDisabledChains();

  /**
   * Whether a *network* refresh is already running for this chain.
   *
   * Hydration is independent. Result admission prevents a delayed cached response from replacing
   * a network result, including when the backend supplies no timestamp. Periodic work checks
   * both queued and running network jobs.
   */
  const isChainRefreshing = (chain: string): boolean => get(refreshState.refreshingChains).has(chain);

  /**
   * Refreshes blockchain balances from the network, as one BLOCKCHAIN_BALANCES activity per chain
   * under a single umbrella.
   *
   * @remarks
   * Chains run on `BALANCES_LANE` at cap 2. Same-chain jobs queue before submission, so detection,
   * querying and frontend result application complete in order without occupying a lane slot while
   * waiting. Different chains remain independent.
   *
   * The umbrella's identity is scope, mode and account revision. Its scope comes from
   * `/blockchains/supported`, which
   * lands before the account walk, so the denominator is honest from the first render — it must
   * never read a store that is still filling.
   *
   * @param payload - what to refresh; an empty `addresses` list means every address, the same as
   * omitting it
   * @param mode - `USER` requests user priority, `PERIODIC` yields to a chain already refreshing,
   * `BACKGROUND` neither
   * @param options - `detect` runs token detection before the query, narrowed to `detectAddresses`
   * when given
   */
  const refreshBlockchainBalances = async (
    payload: BlockchainBalancePayload = {},
    mode: RefreshMode = RefreshMode.BACKGROUND,
    options: RefreshOptions = {},
  ): Promise<void> => {
    const { detect = false, detectAddresses, followUp } = options;
    const { addresses, blockchain, isXpub = false } = payload;
    const chains = blockchain ? arrayify(blockchain) : get(supportedChains).map(chain => chain.id);
    const requestedAddresses = addresses?.length ? addresses : undefined;
    const revisions = Object.fromEntries(chains.map(chain => [chain, revisionOf(chain)]));
    const runRevision = accountRunRevision(chains, revisions);

    const userStarted = mode === RefreshMode.USER;
    const submit = userStarted ? supersedeTask : submitTask;
    const priority = refreshPriority(userStarted);

    /**
     * The id of one chain's refresh job, the one the follow-up depends on.
     *
     * @remarks
     * See {@link chainBalancesActivity} for why detection is part of it. A shared id would also
     * keep `withDetection` writing `lastAutoDetectAt`, so the cooldown would suppress the next
     * sweep too.
     */
    const chainJobId = (chain: string): ActivityId => chainBalancesActivity.id({ chain, detect, detectAddresses, revision: revisions[chain] });

    /**
     * One chain's refresh: token detection when asked, then the network query.
     *
     * @remarks
     * The body runs in statement order, and that order is the contract: an excluded chain is
     * answered before detection so it costs neither a detect nor a query, detection is awaited so
     * the query sees the tokens it found, and cancellation is re-checked afterwards because
     * cancelling the children cannot stop this body. Each of those exits settles SKIPPED or
     * CANCELLED rather than `ok`, so nothing records a completion for work that did not run.
     */
    const chainJob = async (chain: string, parent: ActivityId | undefined): Promise<void> => {
      const id = chainJobId(chain);
      const alreadyRefreshing = isChainRefreshing(chain);
      await refreshState.enqueue(chain, async () => {
        const trackedAddresses = detect && requestedAddresses
          ? new Set(getAccounts(chain).filter(account => account.kind === 'address').map(account => account.address.toLowerCase()))
          : new Set<string>();
        const pendingAddresses = refreshState.pendingAddresses(chain)
          .filter(address => trackedAddresses.has(address.toLowerCase()));
        const allowedAddresses = (addresses: string[]): string[] => Array.from(
          new Map([...addresses, ...pendingAddresses]
            .filter(address => !isAddressExcluded(chain, address))
            .map(address => [address.toLowerCase(), address])).values(),
        );
        const chainAddresses = requestedAddresses ? allowedAddresses(requestedAddresses) : undefined;
        const detectionAddresses = detectAddresses ? allowedAddresses(detectAddresses) : undefined;
        const chainPayload = { addresses: chainAddresses, blockchain: chain, isXpub };
        await submit({
          id,
          parent,
          kind: chainBalancesActivity.kind,
          lane: chainBalancesActivity.laneOf?.({ chain }),
          priority,
          rerunnable: true,
          run: async ({ cancelled, runTask }): Promise<Result<void, TaskError>> => {
            if (mode === RefreshMode.PERIODIC && alreadyRefreshing)
              return err(Skipped({ message: t('actions.balances.blockchain.skipped.busy') }));

            const everyNamedAddressExcluded = chainAddresses?.length === 0;
            if (isChainExcluded(chain) || everyNamedAddressExcluded)
              return err(Skipped({ message: t('actions.balances.blockchain.skipped.disabled') }));

            if (detect)
              await detectForChain(chain, id, detectionAddresses);

            // Cancelled children settle, so the await above resolves either way.
            if (cancelled())
              return err(Cancelled({ message: t('actions.balances.blockchain.cancelled') }));

            return handleRefresh(runTask, chainPayload);
          },
          // Stage-neutral: fixed at submit time, while this job has two stages.
          subtitle: activityLabelFor(msg.$t('task_center.activity.blockchain_balances.chain'), { chain: getChainName(chain) }),
          title: t('task_center.group.blockchain_balances'),
          userStarted,
        });
      });
    };
    const chainWork: Promise<void>[] = [];

    await runActivityBatch(
      {
        id: balancesRunActivity.id({ chains, mode, revision: runRevision }),
        // The chains are the subjects; this only contains them, so it records no completion.
        container: true,
        kind: balancesRunActivity.kind,
        priority,
        subtitle: activityLabelFor(msg.$t('task_center.activity.blockchain_balances.run'), { count: chains.length }),
        title: t('task_center.group.blockchain_balances'),
        userStarted,
      },
      chains,
      async (chain, parent) => {
        const work = chainJob(chain, parent);
        chainWork.push(work);
        return work;
      },
      async (parent): Promise<unknown> => {
        await Promise.all(chainWork);
        return followUp?.(chains.map(chainJobId), parent);
      },
    );
  };

  return {
    refreshBlockchainBalances,
  };
}
