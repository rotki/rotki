import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { DecodableEventType } from '@/modules/history/management/forms/form-guards';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import {
  isEthBlockEvent,
  isEvmEvent,
  isEvmSwapEvent,
  isSolanaEvent,
  isSolanaSwapEvent,
  toLocationAndTxRef,
} from '@/modules/history/event-utils';
import { blockDecodeActivityId, targetedDecodeActivityId } from '@/modules/history/events/tx/decode-activity';
import { type ActivityId, ActivityKind, activityParts } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

/** The decode activity a group row would produce if it were re-decoded right now. */
interface DecodeTarget {
  kind: ActivityKind;
  id: ActivityId;
}

/**
 * Whether the re-decode of *this* group row is in flight.
 *
 * The row tracks no pending state of its own: the activity id is deterministic from the request, so
 * the row rebuilds it from the event it already holds and reads the orchestrator.
 *
 * Build the id with {@link targetedDecodeActivityId}/{@link blockDecodeActivityId} and take it
 * apart with {@link activityParts}; never restate the parts here. A divergence would not fail
 * loudly, the row would simply never light up.
 *
 * Single-row only. A bulk re-decode is one activity over the whole set, so its id is no single
 * row's, and page-level progress covers it.
 */
export function useEventRedecodeStatus(
  event: MaybeRefOrGetter<HistoryEventEntry>,
  groupEvents: MaybeRefOrGetter<HistoryEventEntry[] | undefined>,
): ComputedRef<boolean> {
  const { getChain } = useSupportedChains();
  const { statusOf, version } = useTaskOrchestrator();

  /** The event a re-decode would actually act on — the group header, or the first decodable child. */
  function resolveDecodable(group: HistoryEventEntry, children: HistoryEventEntry[]): DecodableEventType | undefined {
    for (const item of [group, ...children]) {
      if (isEvmEvent(item) || isEvmSwapEvent(item) || isSolanaEvent(item) || isSolanaSwapEvent(item))
        return item;
    }

    return undefined;
  }

  const target = computed<DecodeTarget | undefined>(() => {
    const group = toValue(event);

    if (isEthBlockEvent(group)) {
      return {
        id: blockDecodeActivityId([group.blockNumber]),
        kind: ActivityKind.ETH_BLOCK_DECODING,
      };
    }

    const decodable = resolveDecodable(group, toValue(groupEvents) ?? []);
    if (!decodable)
      return undefined;

    const { location, txRef } = toLocationAndTxRef(decodable);
    return {
      id: targetedDecodeActivityId(getChain(location), [txRef]),
      kind: ActivityKind.TX_DECODING,
    };
  });

  return computed<boolean>(() => {
    get(version); // touch the change counter so the read recomputes on every orchestrator mutation
    const current = get(target);
    return current ? statusOf(current.kind, ...activityParts(current.id)).active : false;
  });
}
