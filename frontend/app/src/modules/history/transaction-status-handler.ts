import type { StateHandler } from '@/modules/core/messaging/interfaces';
import type { UnifiedTransactionStatusData } from '@/modules/core/messaging/types';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { accountSyncActivity } from '@/modules/history/events/tx/sync-activity';
import { periodSteps } from '@/modules/history/tx-query-status-period';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

/**
 * The accounts one message speaks for.
 *
 * Bitcoin batches every address into a single frame while the other subtypes carry one, so the
 * fan-out has to happen before anything per-account is published.
 */
function accountsOf(data: UnifiedTransactionStatusData): ChainAddress[] {
  return data.subtype === 'bitcoin'
    ? data.addresses.map(address => ({ address, chain: data.chain }))
    : [{ address: data.address, chain: data.chain }];
}

export function createTransactionStatusHandler(): StateHandler {
  const { getQueryStatus, setUnifiedTxQueryStatus } = useTxQueryStatusStore();
  const { reportProgress } = useTaskOrchestrator();

  /**
   * Mirror one account's stored entry onto its activity.
   *
   * Read back from the store rather than projected from the frame, so this sees the merged result:
   * the period boundaries an earlier message established, the cancelled entries the store refuses
   * to overwrite, and the canonical chain spelling the id is built from.
   *
   * Progress and detail are split by what the record already owns. How far the query has read is
   * `steps`, so the percentage falls out of the machinery every other activity uses; the range and
   * the sub-query are detail, because nothing on the record can express them.
   */
  function mirrorToActivity(account: ChainAddress): void {
    const entry = getQueryStatus(account);
    if (entry === undefined)
      return;

    const subject = { address: entry.address, chain: entry.chain };

    publishActivityDetail(accountSyncActivity, subject, {
      period: entry.period,
      queryStep: entry.status,
      windowEnd: entry.originalPeriodEnd,
    });

    const steps = periodSteps(entry);
    if (steps !== undefined)
      reportProgress(accountSyncActivity.id(subject), steps);
  }

  return createStateHandler((data) => {
    const accounts = accountsOf(data);
    setUnifiedTxQueryStatus(data);
    accounts.forEach(mirrorToActivity);
  });
}
