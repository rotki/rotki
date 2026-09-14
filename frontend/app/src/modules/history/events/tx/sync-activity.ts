import type { TransactionsQueryStatus } from '@/modules/core/messaging/types';
import type { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { defineActivity } from '@/modules/task-center/core/activity-descriptor';
import {
  ACCOUNT_SYNC_LANE_PREFIX,
  BANK_EVENTS_LANE_PREFIX,
  CHAIN_SYNC_LANE,
  EXCHANGE_EVENTS_LANE_PREFIX,
  familyLane,
} from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind } from '@/modules/task-center/core/types';

/**
 * The identities of everything a history refresh is made of.
 *
 * Shared between the flow declaration, which names these before any of them exists, and the
 * producers that submit them. Composing the same id in both places would not fail loudly if the
 * two drifted: the children would simply stop being gated by, and counted toward, the umbrella
 * that claims them.
 *
 * Declared as descriptors so the lane travels with the id. A chain and its accounts are the same
 * kind and share a key prefix, which is what lets a per-chain reader cover both.
 */

/** One account's sync, within its chain. */
export interface AccountSyncSubject {
  readonly chain: string;
  readonly address: string;
}

/**
 * What an account's sync carries beyond its status and its progress.
 *
 * Deliberately small. How far the query has got is `steps` on the activity, because the record
 * already owns progress and a second copy here would be the duplication `DetailShape` bans. What is
 * left is what steps cannot say: the absolute range being queried, which the panel renders as
 * "from to", and which sub-query is running.
 */
export interface AccountSyncDetail {
  /** The queried range, `[from, cursor]`, in seconds. Absent for a chain that sends no period. */
  readonly period?: readonly [number, number];
  /** The far end of the range, so the panel can render the target rather than only the cursor. */
  readonly windowEnd?: number;
  /** Which sub-query is running, as the backend's own step. */
  readonly queryStep: TransactionsQueryStatus;
}

/** One connected exchange. */
export interface ExchangeEventsSubject {
  readonly location: string;
  readonly name: string;
}

/**
 * What an exchange's event query carries beyond its status.
 *
 * All detail and no progress, unlike {@link AccountSyncDetail}. A status update names the sub-range
 * it is *about to* query rather than how far through the whole query it has reached, and the
 * backend walks those ranges without saying how many there are. Nothing in the stream is a cursor,
 * so any percentage built from it would be invented; the range is worth rendering, a made-up bar is
 * not.
 */
export interface ExchangeEventsDetail {
  /** The sub-range being queried, `[from, to]`, in seconds. Absent until the first status update. */
  readonly period?: readonly [number, number];
  /** Which query this is, as the backend's own type. Empty while the panel is only seeded. */
  readonly eventType: string;
}

/**
 * One chain's sync: the group its accounts and its decode hang from.
 *
 * Its key is the leading slice of {@link accountSyncActivity}'s, so the chain row's id is also the
 * prefix its accounts sit under, and a reader asking about a chain covers the whole group.
 */
export const chainSyncActivity = defineActivity<{ chain: string }, readonly [string]>({
  key: subject => [subject.chain],
  kind: ActivityKind.TX_SYNC,
  lane: () => CHAIN_SYNC_LANE,
});

/**
 * One account's sync within its chain.
 *
 * The lane is the chain's own family, so the family cap gives two concurrent accounts *per chain*
 * rather than two across the run.
 */
export const accountSyncActivity = defineActivity<AccountSyncSubject, readonly [string, string], AccountSyncDetail>({
  key: subject => [subject.chain, subject.address],
  kind: ActivityKind.TX_SYNC,
  lane: subject => familyLane(ACCOUNT_SYNC_LANE_PREFIX, subject.chain),
});

/** One connected exchange's event query. */
export const exchangeEventsActivity = defineActivity<ExchangeEventsSubject, readonly [string, string], ExchangeEventsDetail>({
  key: subject => [subject.location, subject.name],
  kind: ActivityKind.EXCHANGE_EVENTS,
  lane: subject => familyLane(EXCHANGE_EVENTS_LANE_PREFIX, subject.location),
});

/**
 * One bank connection's transaction sync. Same subject and detail as an exchange: a location and
 * a name, and the backend streams the same status frames for it.
 */
export const bankEventsActivity = defineActivity<ExchangeEventsSubject, readonly [string, string], ExchangeEventsDetail>({
  key: subject => [subject.location, subject.name],
  kind: ActivityKind.BANK_EVENTS,
  lane: subject => familyLane(BANK_EVENTS_LANE_PREFIX, subject.location),
});

/**
 * One online-event query (withdrawals, block productions).
 *
 * No lane: these are few and independent, and run unthrottled today.
 */
export const onlineEventsActivity = defineActivity<{ queryType: OnlineHistoryEventsQueryType }, readonly [string]>({
  key: subject => [subject.queryType],
  kind: ActivityKind.ONLINE_EVENTS,
});

/** One chain's sync. See {@link chainSyncActivity}. */
export function chainSyncActivityId(chain: string): ActivityId {
  return chainSyncActivity.id({ chain });
}

/** One account's sync within its chain. See {@link accountSyncActivity}. */
export function accountSyncActivityId(chain: string, address: string): ActivityId {
  return accountSyncActivity.id({ address, chain });
}

/** One connected exchange's event query. See {@link exchangeEventsActivity}. */
export function exchangeEventsActivityId(location: string, name: string): ActivityId {
  return exchangeEventsActivity.id({ location, name });
}

/** One bank connection's transaction sync. See {@link bankEventsActivity}. */
export function bankEventsActivityId(location: string, name: string): ActivityId {
  return bankEventsActivity.id({ location, name });
}

/** One online-event query. See {@link onlineEventsActivity}. */
export function onlineEventsActivityId(queryType: OnlineHistoryEventsQueryType): ActivityId {
  return onlineEventsActivity.id({ queryType });
}
