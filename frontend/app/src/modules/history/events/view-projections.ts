import type { Collection } from '@/modules/core/common/collection';
import type { HighlightType } from '@/modules/history/events/action-types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventRow } from '@/modules/history/events/schemas';
import type { HistoryEventsTableHighlight, HistoryEventsTableSource } from '@/modules/history/events/types';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';

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

export interface UseHistoryEventsTableProjectionOptions {
  /** The view's table toggles, read by `toTableSource`. */
  toggles: MaybeRefOrGetter<HistoryEventsToggles>;
  /** Whether the event groups are loading. */
  groupLoading: MaybeRefOrGetter<boolean>;
  /** The page of event groups to show. */
  groups: MaybeRefOrGetter<Collection<HistoryEventRow>>;
  /** Event identifiers the route narrows the table to, if any. */
  identifiers: MaybeRefOrGetter<string[] | undefined>;
  /** The filter payload the groups were requested with. */
  requestPayload: MaybeRefOrGetter<HistoryEventRequestPayload>;
  /** Group to highlight as a whole. */
  highlightedGroupIdentifier: MaybeRefOrGetter<string | undefined>;
  /** Individual events to highlight. */
  highlightedIdentifiers: MaybeRefOrGetter<string[] | undefined>;
  /** Style per highlighted target. */
  highlightTypes: MaybeRefOrGetter<Record<string, HighlightType> | undefined>;
}

export interface UseHistoryEventsTableProjectionReturn {
  /** What the events table is asked to load, see `toTableSource`. */
  tableSource: ComputedRef<HistoryEventsTableSource>;
  /** What the events table highlights and scrolls to. */
  tableHighlight: ComputedRef<HistoryEventsTableHighlight>;
}

/** Projects the view's filter state onto the two objects the events table takes. */
export function useHistoryEventsTableProjection(options: UseHistoryEventsTableProjectionOptions): UseHistoryEventsTableProjectionReturn {
  const tableSource = computed<HistoryEventsTableSource>(() => toTableSource({
    groupLoading: toValue(options.groupLoading),
    groups: toValue(options.groups),
    identifiers: toValue(options.identifiers),
    requestPayload: toValue(options.requestPayload),
    toggles: toValue(options.toggles),
  }));

  const tableHighlight = computed<HistoryEventsTableHighlight>(() => ({
    groupIdentifier: toValue(options.highlightedGroupIdentifier),
    identifiers: toValue(options.highlightedIdentifiers),
    types: toValue(options.highlightTypes),
  }));

  return { tableHighlight, tableSource };
}
