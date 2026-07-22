import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ParamSource } from '@/modules/core/table/param-sources';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { type HistoryEventEntryType, toSnakeCase, type Writeable } from '@rotki/common';
import { type LocationQuery, RouterLocationLabelsSchema } from '@/modules/core/table/route';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';
import { isValidHistoryEventState } from '@/modules/history/events/mapping/use-history-event-state-mapping';

type Period = { fromTimestamp?: string; toTimestamp?: string } | { fromTimestamp?: number; toTimestamp?: number };

interface HistoryEventSourceDeps {
  duplicateHandlingStatusFromQuery: ComputedRef<DuplicateHandlingStatus | undefined>;
  entryTypes: MaybeRefOrGetter<HistoryEventEntryType[] | undefined>;
  eventSubTypes: MaybeRefOrGetter<string[]>;
  eventTypes: MaybeRefOrGetter<string[]>;
  groupIdentifiersFromQuery: ComputedRef<string[] | undefined>;
  location: MaybeRefOrGetter<string | undefined>;
  /** Written back from the route by the url source's `from`; feeds both a request and a url source. */
  locationLabels: Ref<string[]>;
  missingAcquisitionFromQuery: ComputedRef<string[] | undefined>;
  overlayMode: Ref<OverlayMode>;
  period: MaybeRefOrGetter<Period | undefined>;
  protocols: MaybeRefOrGetter<string[]>;
  route: { query: LocationQuery };
  shouldPreserveHighlights: Ref<boolean>;
  toggles: Ref<HistoryEventsToggles>;
  usedLocationLabels: ComputedRef<string[]>;
  validators: MaybeRefOrGetter<number[] | undefined>;
}

/**
 * Param sources for the history events table, in precedence order: `isDefault`
 * merges below the filter, everything else above it. Replaces the old defaultParams /
 * extraParams / requestParams / queryParamsOnly bags, which differed only in
 * destination and precedence.
 *
 * Lives apart from `useHistoryEventsFilters` only because it is bulky; it has no
 * independent lifecycle and is not meant to be reused.
 */
export function buildHistoryEventSources({
  duplicateHandlingStatusFromQuery,
  entryTypes,
  eventSubTypes,
  eventTypes,
  groupIdentifiersFromQuery,
  location,
  locationLabels,
  missingAcquisitionFromQuery,
  overlayMode,
  period,
  protocols,
  route,
  shouldPreserveHighlights,
  toggles,
  usedLocationLabels,
  validators,
}: HistoryEventSourceDeps): ParamSource[] {
  return [
    {
      isDefault: true,
      to: 'request',
      values: computed<Record<string, unknown>>(() => {
        const types = toValue(entryTypes);
        if (types === undefined || !types)
          return {};

        return { entryTypes: { values: types || [] } };
      }),
    },
    {
      to: 'both',
      values: computed<Record<string, unknown>>(() => {
        const stateMarkers = get(toggles, 'stateMarkers');
        return {
          excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
          groupIdentifiers: get(groupIdentifiersFromQuery),
          ...(stateMarkers.length > 0 ? { stateMarkers } : {}),
        };
      }),
    },
    {
      skipEmpty: true,
      to: 'request',
      values: computed<Record<string, unknown>>(() => {
        const params: Writeable<Partial<HistoryEventRequestPayload>> = {
          aggregateByGroupIds: true,
          counterparties: toValue(protocols),
          eventSubtypes: toValue(eventSubTypes),
          eventTypes: toValue(eventTypes),
          identifiers: get(missingAcquisitionFromQuery),
        };

        const accountsValue = get(usedLocationLabels);

        const locationVal = toValue(location);
        if (locationVal !== undefined)
          params.location = toSnakeCase(locationVal);

        if (accountsValue.length > 0)
          params.locationLabels = accountsValue;

        const periodVal = toValue(period);
        if (periodVal !== undefined) {
          const { fromTimestamp, toTimestamp } = periodVal;
          params.fromTimestamp = fromTimestamp;
          params.toTimestamp = toTimestamp;
        }

        const validatorsVal = toValue(validators);
        if (validatorsVal !== undefined && validatorsVal)
          params.validatorIndices = validatorsVal.map(v => v.toString()) || [];

        return params;
      }),
    },
    {
      // The read direction of the keys this source and the ones above write:
      // pulls locationLabels, state markers and the accounting-overlay mode back
      // out of the route whenever URL state is (re)applied.
      fromQuery(query): void {
        applyHistoryEventRouteQuery(query, { locationLabels, overlayMode, toggles });
      },
      // Preserved in the URL but never sent to the API.
      to: 'url',
      values: computed<Record<string, unknown>>(() => {
        const preserve = get(shouldPreserveHighlights);
        const {
          highlightedAccountingEvent,
          highlightedAssetMovement,
          highlightedInternalTxConflict,
          highlightedNegativeBalanceEvent,
          highlightedPotentialMatch,
        } = get(route).query;

        const stateMarkersValue = get(toggles, 'stateMarkers');
        return {
          duplicateHandlingStatus: get(duplicateHandlingStatusFromQuery),
          groupIdentifiers: get(groupIdentifiersFromQuery)?.join(','),
          ...(preserve
            ? {
                highlightedAssetMovement,
                highlightedAccountingEvent,
                highlightedInternalTxConflict,
                highlightedNegativeBalanceEvent,
                highlightedPotentialMatch,
              }
            : {}),
          locationLabels: get(usedLocationLabels),
          missingAcquisitionIdentifier: get(missingAcquisitionFromQuery)?.join(','),
          // Only the 'balance' mode lands in the URL; 'none' is stripped as an empty value.
          ...(get(overlayMode) === OverlayMode.BALANCE ? { overlay: OverlayMode.BALANCE } : {}),
          ...(stateMarkersValue.length > 0 ? { stateMarkers: stateMarkersValue.join(',') } : {}),
        };
      }),
    },
  ];
}

/**
 * The read direction of the same query binding the sources above write: pulls
 * locationLabels, state markers and the accounting-overlay mode back out of the
 * route. Kept beside `buildHistoryEventSources` so the two halves of each key stay
 * in one file rather than drifting apart across the options object.
 */
function applyHistoryEventRouteQuery(
  query: LocationQuery,
  target: {
    locationLabels: Ref<string[]>;
    overlayMode: Ref<OverlayMode>;
    toggles: Ref<HistoryEventsToggles>;
  },
): void {
  const { locationLabels: parsed } = RouterLocationLabelsSchema.parse(query);
  set(target.locationLabels, !parsed || parsed.length === 0 ? [] : parsed);

  const stateMarkersParam = query.stateMarkers;
  set(target.toggles, {
    ...get(target.toggles),
    stateMarkers: stateMarkersParam && typeof stateMarkersParam === 'string'
      ? stateMarkersParam.split(',').filter(isValidHistoryEventState)
      : [],
  });

  // Restore the accounting-overlay mode from the route (e.g. on back navigation); an
  // empty/absent param resets it to 'none', so a fresh visit starts with the overlay off.
  set(target.overlayMode, query.overlay === OverlayMode.BALANCE ? OverlayMode.BALANCE : OverlayMode.NONE);
}
