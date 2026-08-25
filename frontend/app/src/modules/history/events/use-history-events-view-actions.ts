import type { Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { LinkedMovementMatch, PullLocationTransactionPayload } from '@/modules/history/events/event-payloads';
import type { HistoryEventRow } from '@/modules/history/events/schemas';

/** The debounce on the first load, giving a persisted filter time to reach the route. */
const INITIAL_LOAD_DEBOUNCE = 500;

interface EventIdsUpdate {
  eventIds: number[];
  groupedEvents: Record<string, HistoryEventRow[]>;
  rawEvents?: HistoryEventRow[];
}

export interface UseHistoryEventsViewActionsOptions {
  /** The group collection the table is paging through. */
  groups: Ref<Collection<HistoryEventRow>>;
  /** Whether anything is loading in the background: a decode, or either auto-match. */
  backgroundLoading: Ref<boolean>;
  /** Tell selection mode which events are on the page. */
  setAvailableIds: (ids: number[]) => void;
  /** Tell selection mode how many events the current filter matches in total. */
  setTotalMatchingCount: (count: number) => void;
  /** Reload the events and the locations they came from. */
  fetchDataAndLocations: () => Promise<void>;
  /** Reload the events, re-decoding the transaction the table asked about. */
  fetchDataAndRedecode: (event?: PullLocationTransactionPayload) => Promise<void>;
  /** Refresh everything, which is what a first visit does. */
  refreshAll: () => Promise<void>;
  /** Try to match a movement to the transaction that was just decoded. */
  autoMatchMovement: (movement: LinkedMovementMatch) => Promise<boolean>;
  /** Re-read the unmatched asset movements. */
  refreshUnmatchedAssetMovements: () => Promise<void>;
  /** Re-read the unmatched bridge transactions. */
  refreshUnmatchedBridgeTransactions: () => Promise<void>;
}

export interface UseHistoryEventsViewActionsReturn {
  /** The page's events grouped by transaction, which a delete needs to spot a whole transaction. */
  groupedEventsByTxRef: Readonly<Ref<Record<string, HistoryEventRow[]>>>;
  /** The page's events before grouping, which a delete needs to keep swap groups intact. */
  originalGroups: Readonly<Ref<HistoryEventRow[]>>;
  /** Take what the table reports about the page it just rendered. */
  handleUpdateEventIds: (update: EventIdsUpdate) => void;
  /** Re-decode a transaction, and match the movement it belongs to if it names one. */
  handleRedecode: (event?: PullLocationTransactionPayload) => Promise<void>;
  /** Reload after an asset movement was matched. */
  handleMovementChanged: () => Promise<void>;
  /** Reload after a bridge transaction was matched. */
  handleBridgeChanged: () => Promise<void>;
}

/**
 * What the events page does in response to the table, the dialogs and its own loading.
 *
 * Three are reloads with a different first step. `handleUpdateEventIds` is the page copying what the
 * table rendered, because a delete needs the events that made up a transaction and the grouped shape
 * has already lost them.
 */
export function useHistoryEventsViewActions(
  options: UseHistoryEventsViewActionsOptions,
): UseHistoryEventsViewActionsReturn {
  const {
    autoMatchMovement,
    backgroundLoading,
    fetchDataAndLocations,
    fetchDataAndRedecode,
    groups,
    refreshAll,
    refreshUnmatchedAssetMovements,
    refreshUnmatchedBridgeTransactions,
    setAvailableIds,
    setTotalMatchingCount,
  } = options;

  const route = useRoute();

  // Grouped events for checking complete EVM transactions
  const groupedEventsByTxRef = ref<Record<string, HistoryEventRow[]>>({});
  // Original groups data, which preserves swap groups
  const originalGroups = ref<HistoryEventRow[]>([]);

  function handleUpdateEventIds({ eventIds, groupedEvents, rawEvents }: EventIdsUpdate): void {
    setAvailableIds(eventIds);

    set(groupedEventsByTxRef, groupedEvents);
    // Prefer rawEvents if the table produced them, otherwise fall back to the group page
    set(originalGroups, rawEvents ?? get(groups).data);
  }

  async function handleRedecode(event?: PullLocationTransactionPayload): Promise<void> {
    await fetchDataAndRedecode(event);
    if (event?.linkedMovement) {
      const matched = await autoMatchMovement(event.linkedMovement);
      if (matched)
        await fetchDataAndLocations();
    }
  }

  async function handleMovementChanged(): Promise<void> {
    await refreshUnmatchedAssetMovements();
    await fetchDataAndLocations();
  }

  async function handleBridgeChanged(): Promise<void> {
    await refreshUnmatchedBridgeTransactions();
    await fetchDataAndLocations();
  }

  watchImmediate(groups, (newGroups) => {
    setTotalMatchingCount(newGroups.found);
  });

  // Something that ran in the background has finished, so what the table is showing is stale.
  watch(backgroundLoading, async (isLoading, wasLoading) => {
    if (!isLoading && wasLoading)
      await fetchDataAndLocations();
  });

  // Wait until the route doesn't change anymore to give time for the persisted filter to be set.
  watchDebounced(route, async () => {
    if (import.meta.env.VITE_NO_AUTO_FETCH === 'true')
      await fetchDataAndLocations();
    else
      await refreshAll();
  }, { debounce: INITIAL_LOAD_DEBOUNCE, immediate: true, once: true });

  return {
    groupedEventsByTxRef: shallowReadonly(groupedEventsByTxRef),
    handleBridgeChanged,
    handleMovementChanged,
    handleRedecode,
    handleUpdateEventIds,
    originalGroups: shallowReadonly(originalGroups),
  };
}
