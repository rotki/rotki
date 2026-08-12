import type { ActivityId } from '@/modules/task-center/core/types';
import { msg } from '@/message-key';
import { accountActivityLabel, accountAddActivity, accountImportActivity, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useActivityBatch } from '@/modules/task-center/use-activity-batch';

/**
 * Whether a chain value means "every EVM chain" rather than a real chain. Lives here, beside the
 * batch that knows the pseudo-chain, so a caller never has to import the sentinel to compare
 * against it.
 */
export function isEveryEvmChain(chain: string): boolean {
  return chain === EVM_PSEUDO_CHAIN;
}

interface UseAccountAdditionBatchReturn {
  runAdditionBatch: <TItem, TResult>(
    chain: string,
    items: readonly TItem[],
    addressOf: (item: TItem) => string,
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
    parent?: ActivityId,
  ) => Promise<TResult[]>;
  runEvmAdditionBatch: <TItem, TResult>(
    items: readonly TItem[],
    addressOf: (item: TItem) => string,
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
    parent?: ActivityId,
  ) => Promise<TResult[]>;
  runImportBatch: <TItem, TResult>(
    items: readonly TItem[],
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
  ) => Promise<TResult[]>;
}

/**
 * Fans a bulk addition out as one activity per address under a single umbrella row.
 *
 * It exists so the addition service never has to know what an umbrella id looks like: the id, the
 * label and the pseudo-chain all come from `accounts.activity`, which is also where the children's
 * ids come from. Building them at the call site is how the parent ends up under a different prefix
 * than the children it claims to parent.
 *
 * Throttling is the lane's, not this function's — each child submits onto `accounts-add:<chain>`,
 * capped at 2. Expressing it here as well is the trap documented on `DECODE_LANE`.
 */
export function useAccountAdditionBatch(): UseAccountAdditionBatchReturn {
  const { runActivityBatch } = useActivityBatch();
  const { t } = useI18n({ useScope: 'global' });

  const runAdditionBatch = async <TItem, TResult>(
    chain: string,
    items: readonly TItem[],
    addressOf: (item: TItem) => string,
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
    parent?: ActivityId,
  ): Promise<TResult[]> => runActivityBatch(
    {
      id: accountAddActivity.batchId([chain]),
      kind: accountAddActivity.kind,
      parent,
      subtitle: accountActivityLabel.add(items.map(item => addressOf(item)).join(',\n')),
      title: t('task_center.group.accounts'),
    },
    items,
    run,
  );

  /**
   * A whole CSV import as one umbrella over its rows. The outermost of the three: an import parents
   * its rows, and a row with several addresses parents those under its own per-chain umbrella.
   */
  const runImportBatch = async <TItem, TResult>(
    items: readonly TItem[],
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
  ): Promise<TResult[]> => runActivityBatch(
    {
      id: accountImportActivity.id({ source: 'csv' }),
      kind: accountImportActivity.kind,
      subtitle: activityLabelFor(msg.$t('task_center.activity.accounts.import'), { count: items.length }, items.length),
      title: t('task_center.group.accounts'),
    },
    items,
    run,
  );

  /** The same, for an "add to every EVM chain" request, which is tracked under the pseudo-chain. */
  const runEvmAdditionBatch = async <TItem, TResult>(
    items: readonly TItem[],
    addressOf: (item: TItem) => string,
    run: (item: TItem, parent: ActivityId | undefined) => Promise<TResult>,
    parent?: ActivityId,
  ): Promise<TResult[]> => runAdditionBatch(EVM_PSEUDO_CHAIN, items, addressOf, run, parent);

  return { runAdditionBatch, runEvmAdditionBatch, runImportBatch };
}
