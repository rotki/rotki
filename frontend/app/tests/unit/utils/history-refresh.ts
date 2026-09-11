import { neverSettles } from '@test/utils/never-settles';
import { err, ok, type Result } from 'plainfp/result';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { decodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { historySyncFlow } from '@/modules/history/events/tx/history-sync.flow';
import { accountSyncActivityId, chainSyncActivityId } from '@/modules/history/events/tx/sync-activity';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

/** How a declared leaf ends, or that it has not. */
export type LeafOutcome = 'running' | 'complete' | 'failed' | 'cancelled';

const flush = async (): Promise<void> => new Promise(resolve => setTimeout(resolve, 0));

function runFor(outcome: LeafOutcome): () => Promise<Result<unknown, TaskError>> {
  if (outcome === 'running')
    return async () => neverSettles();
  if (outcome === 'complete')
    return async () => ok(undefined);
  if (outcome === 'cancelled')
    return async () => err(Cancelled({ message: 'stopped' }));
  return async () => err(TaskFailed({ message: 'the backend said no' }));
}

/**
 * Submit a history refresh the way `history-sync.flow.ts` declares one: the umbrella, a chain per
 * entry, an account beneath each chain, and optionally a decode per chain.
 *
 * @remarks
 * Shared because both the sync panel and the dashboard read their progress off this tree, and a
 * second copy of the fixture is how the two stop agreeing about what a refresh looks like.
 *
 * The accounts and decodes are the leaves the rollup counts, so each names its own outcome. Keep
 * fixtures to two chains: `CHAIN_SYNC_LANE` caps concurrency at two, and a third chain would sit
 * PENDING with its accounts ineligible. That is realistic, but rarely what a case is about.
 *
 * @param chains - chain to account-address to how that account's sync ends
 * @param decodes - chain to how that chain's decode ends; omit for a refresh with no decode
 */
export async function submitRefresh(
  chains: Record<string, Record<string, LeafOutcome>>,
  decodes: Record<string, LeafOutcome> = {},
): Promise<void> {
  const orchestrator = useTaskOrchestrator();
  const umbrella = historySyncFlow.id();

  orchestrator.submit({
    container: true,
    id: umbrella,
    kind: ActivityKind.HISTORY_SYNC,
    run: async () => ok(undefined),
    title: 'refresh',
  });

  for (const [chain, accounts] of Object.entries(chains)) {
    orchestrator.submit({
      id: chainSyncActivityId(chain),
      kind: ActivityKind.TX_SYNC,
      parent: umbrella,
      run: async () => ok(undefined),
      title: chain,
    });

    for (const [address, outcome] of Object.entries(accounts)) {
      orchestrator.submit({
        id: accountSyncActivityId(chain, address),
        kind: ActivityKind.TX_SYNC,
        parent: chainSyncActivityId(chain),
        run: runFor(outcome),
        title: address,
      });
    }
  }

  for (const [chain, outcome] of Object.entries(decodes)) {
    orchestrator.submit({
      id: decodeActivityId(chain),
      kind: ActivityKind.TX_DECODING,
      parent: chainSyncActivityId(chain),
      run: runFor(outcome),
      title: `decode ${chain}`,
    });
  }

  await flush();
}
