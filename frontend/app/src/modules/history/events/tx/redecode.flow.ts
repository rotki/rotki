import type { FlowChild, HistoryFlow } from '@/modules/history/events/flows';
import { msg } from '@/message-key';
import { decodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';

/** The `ignoreCache` a re-decode submits with, and therefore the one its children must be named for. */
const IGNORE_CACHE = true;

/**
 * Re-derive decodable chains' events from transactions already in the database.
 *
 * One flow with a scope: "re-decode everything" and "re-decode these chains" are the same work over
 * a different set, and the set belongs in the identity — two requests for the same chains dedup, a
 * scoped and a full request must not.
 *
 * Reset-bearing: the backend deletes each location's non-customized events before re-deriving
 * (`reset_events_for_redecode`), so this must never overlap matching.
 *
 * Pulls nothing new — that is `refresh` (forward) and `re-pull` (a past range).
 */
export const redecodeFlow: HistoryFlow<readonly string[], string> = {
  /**
   * One decode per chain in the resolved set. The ids come from {@link decodeActivityId}, the same
   * constructor the mechanism submits under, so the parent gate cannot be broken by the two drifting
   * apart.
   */
  children: (chains: readonly string[]): readonly FlowChild<string>[] => chains.map(chain => ({
    id: decodeActivityId(chain, IGNORE_CACHE),
    kind: ActivityKind.TX_DECODING,
    payload: chain,
  })),
  /**
   * Chains are sorted, so the same set asked for in a different order is the same run; and joined
   * with a comma rather than the id separator, so `activityParts` recovers the set as one part
   * instead of shredding it into members.
   */
  id: (chains?: readonly string[]): ActivityId => chains === undefined || chains.length === 0
    ? makeActivityId(ActivityKind.REDECODE, ActivityPart.ALL)
    : makeActivityId(ActivityKind.REDECODE, ActivityPart.CHAINS, [...chains].sort().join(',')),
  kind: ActivityKind.REDECODE,
  resets: true,
  titleKey: msg.$t('task_center.group.redecode'),
};
