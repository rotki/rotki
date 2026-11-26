import type { MaybeRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ParamSource } from '@/modules/core/table/param-sources';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/history/events/history-event-filter-keys';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

interface UseHistoryEventsGroupsTableOptions {
  /** The pill-bar fields; the table reads the url shape of the filter bag off them. */
  fields: MaybeRefOrGetter<FieldDef[]>;
  /** The filter bag the pill bar is bound to. */
  filters: Ref<Filters>;
  /** Whether this is the main history page; only then is the table state synced with the route. */
  mainPage: MaybeRefOrGetter<boolean>;
  /** The request and url param sources, in precedence order. */
  params: ParamSource[];
}

export type UseHistoryEventsGroupsTableReturn = ReturnType<typeof useServerTable<HistoryEventRow, HistoryEventRequestPayload, Filters>>;

const GROUPS_CANCEL_TAG = 'history-events-groups';

/**
 * The server table of history event groups: fetches through a cancellable tag and keeps the
 * one-off navigation params out of the remembered filter.
 */
export function useHistoryEventsGroupsTable(options: UseHistoryEventsGroupsTableOptions): UseHistoryEventsGroupsTableReturn {
  const { fields, filters, mainPage, params } = options;
  const { fetchHistoryEvents } = useHistoryEvents();

  const fetchHistoryEventsTagged = async (
    payload: MaybeRef<HistoryEventRequestPayload>,
  ): ReturnType<typeof fetchHistoryEvents> =>
    fetchHistoryEvents(payload, { tags: [GROUPS_CANCEL_TAG] });

  return useServerTable<
    HistoryEventRow,
    HistoryEventRequestPayload,
    Filters
  >({
    fetch: fetchHistoryEventsTagged,
    fields,
    filters,
    params,
    persist: {
      keys: {
        duplicateHandlingStatus: 'never',
        groupIdentifiers: 'never',
        highlightedAccountingEvent: 'never',
        highlightedAssetMovement: 'never',
        highlightedInternalTxConflict: 'never',
        highlightedGroupIdentifier: 'never',
        highlightedNegativeBalanceEvent: 'never',
        highlightedPotentialMatch: 'never',
        missingAcquisitionIdentifier: 'never',
        // Keep the overlay out of the remembered filter so it never persists across sessions.
        overlay: 'never',
        targetGroupIdentifier: 'never',
        txRefs: 'untilChanged',
      },
      tableId: TableId.HISTORY,
    },
    request: {
      cancelTag: GROUPS_CANCEL_TAG,
    },
    urlState: routeWhen(mainPage),
  });
}
