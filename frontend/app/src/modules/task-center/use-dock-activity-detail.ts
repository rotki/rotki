import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { toSentenceCase } from '@rotki/common';
import { type MessageKey, msg } from '@/message-key';
import { TransactionsQueryStatus } from '@/modules/core/messaging/types/status-types';
import { decodeActivity } from '@/modules/history/events/tx/decode-activity';
import { accountSyncActivity, bankEventsActivity, exchangeEventsActivity } from '@/modules/history/events/tx/sync-activity';
import { protocolCacheActivity, type ProtocolCacheDetail } from '@/modules/history/protocol-cache-activity';
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

/** What a running row can say beyond its label and bar, from the detail its producer streams. */
export type DockDetail =
  | { readonly type: 'query'; readonly step: string | undefined; readonly period: DockDetailPeriod | undefined }
  | { readonly type: 'caches'; readonly current: DockDetailCache; readonly more: number };

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

/** The first cache still filling, and how many more are, or `undefined` when none is. */
function cachesDetail(detail: ProtocolCacheDetail | undefined): DockDetail | undefined {
  const filling = detail?.protocols.filter(row => row.processed < row.total) ?? [];
  const [current] = filling;
  if (current === undefined)
    return undefined;
  return { current, more: filling.length - 1, type: 'caches' };
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
 * Only while the activity runs: the detail describes a query in flight, and a settled row has its
 * outcome to show instead.
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

  function decode(current: Activity): DockDetail | undefined {
    const [chain] = activityParts(current.id);
    const subject = [false, true]
      .map(ignoreCache => ({ chain: chain ?? '', ignoreCache }))
      .find(candidate => decodeActivity.id(candidate) === current.id);
    return subject ? cachesDetail(peekActivityDetail(decodeActivity, subject)) : undefined;
  }

  function protocolCache(current: Activity): DockDetail | undefined {
    return current.id === protocolCacheActivity.id() ? cachesDetail(peekActivityDetail(protocolCacheActivity, undefined)) : undefined;
  }

  /** The kinds whose producers stream detail, each read back through its own descriptor. */
  const READERS: Partial<Record<ActivityKind, (current: Activity) => DockDetail | undefined>> = {
    [ActivityKind.BANK_EVENTS]: events,
    [ActivityKind.EXCHANGE_EVENTS]: events,
    [ActivityKind.PROTOCOL_CACHE]: protocolCache,
    [ActivityKind.TX_DECODING]: decode,
    [ActivityKind.TX_SYNC]: accountSync,
  };

  return computed<DockDetail | undefined>(() => {
    const current = toValue(activity);
    return current.status === ActivityStatus.RUNNING ? READERS[current.kind]?.(current) : undefined;
  });
}
