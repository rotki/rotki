import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableSource } from '@/modules/history/events/types';

export interface TableSourceInput {
  toggles: HistoryEventsToggles;
  groupLoading: boolean;
  groups: Collection<HistoryEventRow>;
  identifiers?: string[];
  requestPayload: HistoryEventRequestPayload;
}

/**
 * What the events table is asked to load.
 *
 * `showIgnoredAssets` is the inverse of what the table takes. `matchExactEvents` decides whether the
 * filter payload is passed down at all: without it the table loads every event in the selected
 * groups, with it the same filter is applied again to the events inside them.
 */
export function toTableSource(input: TableSourceInput): HistoryEventsTableSource {
  const { groupLoading, groups, identifiers, requestPayload, toggles } = input;

  return {
    excludeIgnored: !toggles.showIgnoredAssets,
    groupLoading,
    groups,
    identifiers,
    requestPayload: toggles.matchExactEvents ? requestPayload : undefined,
  };
}
