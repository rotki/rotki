import type { ActivitySubject } from '@/modules/task-center/activity-subject';
import { type MessageKey, msg } from '@/message-key';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import { ActivityKind, type ActivityText } from '@/modules/task-center/core/types';
import { type BackgroundTask, BackgroundTaskKind, backgroundTaskKindOf } from './background-task-types';

function subjectText(task: BackgroundTask, field: string): string | undefined {
  const value = task.subject[field];
  return value === undefined ? undefined : String(value);
}

type SubjectField = 'address' | 'chain' | 'location';

/**
 * The subject fields each kind puts into its id after the kind and the backend id, in order. A kind
 * left out has no icon or link to give its row.
 */
const SUBJECT_FIELDS: Partial<Record<BackgroundTaskKind, readonly SubjectField[]>> = {
  [BackgroundTaskKind.EVM_RECEIPTS]: ['chain'],
  [BackgroundTaskKind.EVM_TRANSACTIONS]: ['chain', 'address'],
  [BackgroundTaskKind.EXCHANGE_HISTORY]: ['location'],
  [BackgroundTaskKind.TRANSACTION_DECODING]: ['chain'],
  [BackgroundTaskKind.XPUB_DERIVATION]: ['chain'],
};

/** The subject values that go into the id, up to the first one the task lacks, so none shifts into another's place. */
function subjectParts(task: BackgroundTask): string[] {
  const parts: string[] = [];
  for (const field of SUBJECT_FIELDS[backgroundTaskKindOf(task.kind)] ?? []) {
    const value = subjectText(task, field);
    if (value === undefined)
      break;
    parts.push(value);
  }
  return parts;
}

/**
 * One backend task manager task, mirrored as a dock row.
 *
 * @remarks
 * Keyed by the backend id, which alone is unique within a login. The kind and the subject follow
 * it so the row's chain or exchange icon and its address link can be read back from the id, the way
 * every other row's are.
 */
export const backgroundTaskActivity = defineActivity({
  key: (task: BackgroundTask) => [backgroundTaskKindOf(task.kind), task.id, ...subjectParts(task)],
  kind: ActivityKind.BACKGROUND_TASK,
});

/** What a background task acts on, read back from its id parts: `[kind, id, ...subject]`. */
export function backgroundTaskSubject([kind = '', , ...values]: string[]): ActivitySubject | undefined {
  const fields = SUBJECT_FIELDS[backgroundTaskKindOf(kind)] ?? [];
  const entries = fields.flatMap((field, index) => {
    const value = values[index];
    return value === undefined ? [] : [[field, value] as const];
  });
  return entries.length === 0 ? undefined : Object.fromEntries(entries);
}

/** The description of each kind that has a row; {@link BackgroundTaskKind.OTHER} has none of its own. */
const LABELS: Readonly<Record<Exclude<BackgroundTaskKind, typeof BackgroundTaskKind.OTHER>, MessageKey>> = {
  [BackgroundTaskKind.CALENDAR_SYNC]: msg.$t('task_center.activity.background_task.calendar_sync'),
  [BackgroundTaskKind.DATA_UPDATES]: msg.$t('task_center.activity.background_task.data_updates'),
  [BackgroundTaskKind.DB_UPLOAD]: msg.$t('task_center.activity.background_task.db_upload'),
  [BackgroundTaskKind.ETH_STAKING]: msg.$t('task_center.activity.background_task.eth_staking'),
  [BackgroundTaskKind.EVM_ACCOUNTS_DETECTION]: msg.$t('task_center.activity.background_task.evm_accounts_detection'),
  [BackgroundTaskKind.EVM_RECEIPTS]: msg.$t('task_center.activity.background_task.evm_receipts'),
  [BackgroundTaskKind.EVM_TRANSACTIONS]: msg.$t('task_center.activity.background_task.evm_transactions'),
  [BackgroundTaskKind.EXCHANGE_HISTORY]: msg.$t('task_center.activity.background_task.exchange_history'),
  [BackgroundTaskKind.GNOSIS_PAY_EVENTS]: msg.$t('task_center.activity.background_task.gnosis_pay_events'),
  [BackgroundTaskKind.HISTORICAL_BALANCES]: msg.$t('task_center.activity.background_task.historical_balances'),
  [BackgroundTaskKind.MONERIUM_ORDERS]: msg.$t('task_center.activity.background_task.monerium_orders'),
  [BackgroundTaskKind.SNAPSHOT_BALANCES]: msg.$t('task_center.activity.background_task.snapshot_balances'),
  [BackgroundTaskKind.TRANSACTION_DECODING]: msg.$t('task_center.activity.background_task.transaction_decoding'),
  [BackgroundTaskKind.XPUB_DERIVATION]: msg.$t('task_center.activity.background_task.xpub_derivation'),
};

/**
 * The short name each kind's row is titled with, as other rows are by their job ("Transaction sync").
 * Every row already sits under the "Background tasks" group, so the title says what the task does.
 */
const TITLES: Readonly<Record<BackgroundTaskKind, MessageKey>> = {
  [BackgroundTaskKind.CALENDAR_SYNC]: msg.$t('task_center.background_task.calendar_sync'),
  [BackgroundTaskKind.DATA_UPDATES]: msg.$t('task_center.background_task.data_updates'),
  [BackgroundTaskKind.DB_UPLOAD]: msg.$t('task_center.background_task.db_upload'),
  [BackgroundTaskKind.ETH_STAKING]: msg.$t('task_center.background_task.eth_staking'),
  [BackgroundTaskKind.EVM_ACCOUNTS_DETECTION]: msg.$t('task_center.background_task.evm_accounts_detection'),
  [BackgroundTaskKind.EVM_RECEIPTS]: msg.$t('task_center.background_task.evm_receipts'),
  [BackgroundTaskKind.EVM_TRANSACTIONS]: msg.$t('task_center.background_task.evm_transactions'),
  [BackgroundTaskKind.EXCHANGE_HISTORY]: msg.$t('task_center.background_task.exchange_history'),
  [BackgroundTaskKind.GNOSIS_PAY_EVENTS]: msg.$t('task_center.background_task.gnosis_pay_events'),
  [BackgroundTaskKind.HISTORICAL_BALANCES]: msg.$t('task_center.background_task.historical_balances'),
  [BackgroundTaskKind.MONERIUM_ORDERS]: msg.$t('task_center.background_task.monerium_orders'),
  [BackgroundTaskKind.OTHER]: msg.$t('task_center.background_task.other'),
  [BackgroundTaskKind.SNAPSHOT_BALANCES]: msg.$t('task_center.background_task.snapshot_balances'),
  [BackgroundTaskKind.TRANSACTION_DECODING]: msg.$t('task_center.background_task.transaction_decoding'),
  [BackgroundTaskKind.XPUB_DERIVATION]: msg.$t('task_center.background_task.xpub_derivation'),
};

/** The key of the row's title. */
export function backgroundTaskTitle(task: BackgroundTask): MessageKey {
  return TITLES[backgroundTaskKindOf(task.kind)];
}

interface LabelParams {
  readonly params: Record<string, unknown>;
  readonly plural?: number;
}

type LabelParamsOf = (task: BackgroundTask, getChainName: (chain: string) => string) => LabelParams;

function countOnChain(task: BackgroundTask, getChainName: (chain: string) => string): LabelParams {
  const count = typeof task.subject.count === 'number' ? task.subject.count : 0;
  return { params: { chain: getChainName(subjectText(task, 'chain') ?? ''), count }, plural: count };
}

/** The values each kind's description names; a kind left out names none. */
const LABEL_PARAMS: Partial<Record<BackgroundTaskKind, LabelParamsOf>> = {
  [BackgroundTaskKind.EVM_RECEIPTS]: countOnChain,
  /** The address alone, so the row can draw it as a link; the chain shows as the row's icon. */
  [BackgroundTaskKind.EVM_TRANSACTIONS]: task => ({ params: { address: subjectText(task, 'address') } }),
  [BackgroundTaskKind.EXCHANGE_HISTORY]: task => ({ params: { name: subjectText(task, 'name') } }),
  [BackgroundTaskKind.TRANSACTION_DECODING]: countOnChain,
  [BackgroundTaskKind.XPUB_DERIVATION]: (task, getChainName) => ({ params: { chain: getChainName(subjectText(task, 'chain') ?? '') } }),
};

/**
 * The row's description.
 *
 * @remarks
 * A task of a kind this build does not describe falls back to the backend's own name for it, which
 * is English. Only a failure of such a task gets a row, so that is the one place it shows.
 * `getChainName` resolves a chain id to its display name, which the subtitle carries as a value.
 */
export function backgroundTaskLabel(task: BackgroundTask, getChainName: (chain: string) => string): ActivityText {
  const kind = backgroundTaskKindOf(task.kind);
  if (kind === BackgroundTaskKind.OTHER)
    return task.name;

  const { params, plural } = LABEL_PARAMS[kind]?.(task, getChainName) ?? {};
  return activityLabelFor(LABELS[kind], params, plural);
}
