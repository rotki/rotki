import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { toSentenceCase } from '@rotki/common';
import { type MessageKey, msg } from '@/message-key';
import { accountAddActivity, type AccountAdditionDetail, type AccountSubject } from '@/modules/accounts/accounts.activity';
import { TransactionsQueryStatus } from '@/modules/core/messaging/types/status-types';
import { decodeActivity } from '@/modules/history/events/tx/decode-activity';
import { accountSyncActivity, bankEventsActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { protocolCacheActivity, type ProtocolCacheDetail } from '@/modules/history/protocol-cache-activity';
import { activitySubject } from '@/modules/task-center/activity-subject';
import { isTerminalStatus, needsAttention } from '@/modules/task-center/core/status';
import { type Activity, ActivityKind, activityParts, ActivityStatus } from '@/modules/task-center/core/types';
import { peekActivityDetail } from '@/modules/task-center/use-activity-detail';

/** A queried range. `from` is absent when the query has not moved past its start yet. */
interface DockDetailPeriod {
  readonly from: number | undefined;
  readonly to: number;
}

/** One protocol cache being filled, as the row names it. */
interface DockDetailCache {
  readonly protocol: string;
  readonly chain: string;
  readonly processed: number;
  readonly total: number;
}

/** What a row can say beyond its label and bar, from the detail its producer streams. */
export type DockDetail =
  | { readonly type: 'query'; readonly step: string | undefined; readonly period: DockDetailPeriod | undefined }
  | {
    readonly type: 'caches';
    readonly filling: DockDetailCache[];
    readonly filled: DockDetailCache[];
    /** Left unfinished by work that has settled, cancelled or failed, so no longer filling. */
    readonly stopped: DockDetailCache[];
  }
  | { readonly type: 'addition' } & AccountAdditionDetail
  /** An address the user asked to add that ended up tracked nowhere, which the row offers to track on a chain. */
  | { readonly type: 'untracked'; readonly address: string };

/** The step each transaction query status names, as an i18n key; `undefined` for a status that is not a step. */
const SYNC_STEP: Record<TransactionsQueryStatus, MessageKey | undefined> = {
  [TransactionsQueryStatus.ACCOUNT_CHANGE]: undefined,
  [TransactionsQueryStatus.CANCELLED]: undefined,
  [TransactionsQueryStatus.DECODING_TRANSACTIONS_FINISHED]: undefined,
  [TransactionsQueryStatus.DECODING_TRANSACTIONS_STARTED]: msg.$t('task_dock.detail.decoding'),
  [TransactionsQueryStatus.FAILED]: undefined,
  [TransactionsQueryStatus.QUERYING_EVM_TOKENS_TRANSACTIONS]: msg.$t('task_dock.detail.querying_tokens'),
  [TransactionsQueryStatus.QUERYING_INTERNAL_TRANSACTIONS]: msg.$t('task_dock.detail.querying_internal'),
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS]: msg.$t('task_dock.detail.querying_transactions'),
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED]: undefined,
  [TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED]: msg.$t('task_dock.detail.querying_transactions'),
};

/**
 * An account's range as the row shows it: from the cursor it has reached to the far end of the
 * window, with no start while the cursor has not moved past where it began.
 */
function syncPeriod(period: readonly [number, number] | undefined, windowEnd: number | undefined): DockDetailPeriod | undefined {
  if (period === undefined)
    return undefined;

  const [start, cursor] = period;
  return { from: cursor === 0 || cursor === start ? undefined : cursor, to: windowEnd ?? cursor };
}

/**
 * Every cache the work has touched, split into full ones and unfinished ones, or `undefined` when
 * there are none. An unfinished cache is filling while the work runs and stopped once it settles.
 */
function cachesDetail(rows: ProtocolCacheDetail['protocols'], running: boolean): DockDetail | undefined {
  if (rows.length === 0)
    return undefined;

  const unfinished = rows.filter(row => row.processed < row.total);
  return {
    filled: rows.filter(row => row.processed >= row.total),
    filling: running ? unfinished : [],
    stopped: running ? [] : unfinished,
    type: 'caches',
  };
}

/**
 * The protocol caches an activity has filled or is filling, read through the descriptor that
 * published them; empty for a kind that fills none. A decode's subject is rebuilt for both cache
 * variants and kept only where the descriptor mints the activity's own id.
 */
export function activityCaches(activity: Activity): ProtocolCacheDetail['protocols'] {
  if (activity.kind === ActivityKind.PROTOCOL_CACHE)
    return activity.id === protocolCacheActivity.id() ? peekActivityDetail(protocolCacheActivity, undefined)?.protocols ?? [] : [];

  if (activity.kind !== ActivityKind.TX_DECODING)
    return [];

  const [chain] = activityParts(activity.id);
  const subject = [false, true]
    .map(ignoreCache => ({ chain: chain ?? '', ignoreCache }))
    .find(candidate => decodeActivity.id(candidate) === activity.id);
  return subject ? peekActivityDetail(decodeActivity, subject)?.protocols ?? [] : [];
}

/**
 * The extra line a running dock row shows, read from the activity detail channel.
 *
 * @remarks
 * The detail was already streamed for the old sync panel's lists: which sub-query an account is on
 * and the range it has reached, which query an exchange or bank is running, and which protocol
 * caches a decode is filling. Each is read back through the descriptor that published it, with the
 * subject rebuilt from the activity's id and kept only when the descriptor mints that same id, so a
 * chain-level row never picks up an account's detail by sharing a prefix.
 *
 * A query's step and range show only while the activity runs, since they describe a query in
 * flight and a settled row has its outcome to show instead. The caches stay once it settles, as the
 * record of what the work filled, the way the sync panel kept its completed list. An account
 * addition's chains show only once it has completed, since they are its outcome.
 */
export function useDockActivityDetail(activity: MaybeRefOrGetter<Activity>): ComputedRef<DockDetail | undefined> {
  const { t } = useI18n({ useScope: 'global' });

  function accountSync(current: Activity): DockDetail | undefined {
    const [chain, address] = activityParts(current.id);
    const subject = { address: address ?? '', chain: chain ?? '' };
    if (address === undefined || accountSyncActivity.id(subject) !== current.id)
      return undefined;

    const detail = peekActivityDetail(accountSyncActivity, subject);
    if (detail === undefined)
      return undefined;

    const step = SYNC_STEP[detail.queryStep];
    return { period: syncPeriod(detail.period, detail.windowEnd), step: step ? t(step) : undefined, type: 'query' };
  }

  function events(current: Activity): DockDetail | undefined {
    const descriptor = current.kind === ActivityKind.BANK_EVENTS ? bankEventsActivity : exchangeEventsActivity;
    const [location, name] = activityParts(current.id);
    const subject = { location: location ?? '', name: name ?? '' };
    if (name === undefined || descriptor.id(subject) !== current.id)
      return undefined;

    const detail = peekActivityDetail(descriptor, subject);
    if (detail === undefined)
      return undefined;

    const type = detail.eventType === 'history_query' ? t('common.events') : toSentenceCase(detail.eventType);
    return {
      period: detail.period ? { from: detail.period[0], to: detail.period[1] } : undefined,
      step: detail.eventType ? t('task_dock.detail.querying_event_type', { type }) : undefined,
      type: 'query',
    };
  }

  /**
   * Where an "every EVM chain" addition landed. Rebuilt for that subject only, since it is the one
   * addition that publishes a breakdown; any other account id fails the id check and reads nothing.
   */
  function accountAddition(current: Activity): DockDetail | undefined {
    const [, chain, address] = activityParts(current.id);
    const subject: AccountSubject = { chain: chain ?? '', target: { address: address ?? '', kind: 'address' } };
    if (address === undefined || accountAddActivity.id(subject) !== current.id)
      return undefined;

    const detail = peekActivityDetail(accountAddActivity, subject);
    return detail === undefined ? undefined : { ...detail, type: 'addition' };
  }

  /** A single address whose addition asked for attention; the row offers to track it on a chain. */
  function untracked(current: Activity): DockDetail | undefined {
    const address = activitySubject(current)?.address;
    return address === undefined || current.status !== ActivityStatus.SKIPPED ? undefined : { address, type: 'untracked' };
  }

  /** The kinds whose producers stream a query in flight, each read back through its own descriptor. */
  const QUERY_READERS: Partial<Record<ActivityKind, (current: Activity) => DockDetail | undefined>> = {
    [ActivityKind.BANK_EVENTS]: events,
    [ActivityKind.EXCHANGE_EVENTS]: events,
    [ActivityKind.TX_SYNC]: accountSync,
  };

  return computed<DockDetail | undefined>(() => {
    const current = toValue(activity);
    const cached = cachesDetail(activityCaches(current), !isTerminalStatus(current.status));
    if (cached !== undefined)
      return cached;
    if (current.kind === ActivityKind.ACCOUNTS && current.status === ActivityStatus.COMPLETE)
      return accountAddition(current);
    if (current.kind === ActivityKind.ACCOUNTS && needsAttention(current))
      return untracked(current);
    return current.status === ActivityStatus.RUNNING ? QUERY_READERS[current.kind]?.(current) : undefined;
  });
}
