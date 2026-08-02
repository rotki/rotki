import type { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { type ActivityId, ActivityKind, makeActivityId } from '@/modules/task-center/core/types';

/**
 * The identities of everything a history refresh is made of.
 *
 * Shared between the flow declaration, which names these before any of them exists, and the
 * producers that submit them. Composing the same id in both places would not fail loudly if the
 * two drifted — the children would simply stop being gated by, and counted toward, the umbrella
 * that claims them.
 */

/** One chain's sync: the group its accounts and its decode hang from. */
export function chainSyncActivityId(chain: string): ActivityId {
  return makeActivityId(ActivityKind.TX_SYNC, chain);
}

/** One account's sync within its chain. */
export function accountSyncActivityId(chain: string, address: string): ActivityId {
  return makeActivityId(ActivityKind.TX_SYNC, chain, address);
}

/** One connected exchange's event query. */
export function exchangeEventsActivityId(location: string, name: string): ActivityId {
  return makeActivityId(ActivityKind.EXCHANGE_EVENTS, location, name);
}

/** One online-event query (withdrawals, block productions). */
export function onlineEventsActivityId(queryType: OnlineHistoryEventsQueryType): ActivityId {
  return makeActivityId(ActivityKind.ONLINE_EVENTS, queryType);
}
