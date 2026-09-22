import type { StateHandler } from '@/modules/core/messaging/interfaces';
import type { ChainAddress } from '@/modules/history/events/event-payloads';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { TransactionsQueryStatus, type UnifiedTransactionStatusData } from '@/modules/core/messaging/types';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { accountSyncActivity } from '@/modules/history/events/tx/sync-activity';
import { mergeTxFrame, periodSteps, type TxAccountTracking } from '@/modules/history/tx-query-status-period';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useLiveActivityEntries } from '@/modules/task-center/use-live-activity-entries';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

/**
 * The accounts one message speaks for, under the lowercased chain their activities are keyed by.
 *
 * Bitcoin batches every address into a single frame while the other subtypes carry one, so the
 * fan-out has to happen before anything per-account is published.
 */
function accountsOf(data: UnifiedTransactionStatusData): ChainAddress[] {
  const chain = data.chain.toLowerCase();
  return data.subtype === 'bitcoin'
    ? data.addresses.map(address => ({ address, chain }))
    : [{ address: data.address, chain }];
}

/**
 * Turns the backend's transaction query frames into each account's sync progress.
 *
 * @remarks
 * A frame only updates an account whose sync activity is live. One that lands after the sync ended,
 * or after the user cancelled it, finds nothing to update, so a cancelled account keeps the detail
 * it had reached instead of being revived by a late message. What a run's frames establish, such as
 * the window its progress is measured against, is kept for as long as that activity is live and
 * dropped when it settles; see `useLiveActivityEntries`.
 *
 * Progress and detail are split by what the record already owns. How far the query has read is
 * `steps`, so the percentage falls out of the machinery every other activity uses; the range and the
 * sub-query are detail, because nothing on the record can express them.
 */
export function createTransactionStatusHandler(): StateHandler {
  const { reportProgress } = useTaskOrchestrator();
  const tracking = useLiveActivityEntries<TxAccountTracking>();

  function track(data: UnifiedTransactionStatusData, account: ChainAddress, now: number): void {
    const address = { kind: accountSyncActivity.kind, parts: accountSyncActivity.partsOf(account) };
    if (!tracking.isLive(address))
      return;

    const entry = mergeTxFrame(data, tracking.read(address), now);
    tracking.write(address, entry);

    publishActivityDetail(accountSyncActivity, account, {
      period: entry.period,
      queryStep: entry.status,
      windowEnd: entry.originalPeriodEnd,
    });

    const steps = periodSteps(entry);
    if (steps !== undefined)
      reportProgress(accountSyncActivity.id(account), steps);
  }

  return createStateHandler((data) => {
    if (data.status === TransactionsQueryStatus.ACCOUNT_CHANGE)
      return;

    const now = millisecondsToSeconds(Date.now());
    for (const account of accountsOf(data))
      track(data, account, now);
  });
}
