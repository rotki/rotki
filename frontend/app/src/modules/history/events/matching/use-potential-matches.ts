import type { MaybeRefOrGetter, Ref } from 'vue';
import type { MatchingFlow, MatchSuggestions, PotentialMatchRow, UnmatchedEventGroup } from './types';
import type { HistoryEventCollectionRow } from '@/modules/history/events/schemas';
import { bigNumberify } from '@rotki/common';
import { parseNumericInput } from '@/modules/core/common/data/bignumbers';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { useAssetMovementMatchingApi } from '@/modules/history/api/events/use-asset-movement-matching-api';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { getEventEntryFromCollection } from '@/modules/history/event-utils';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useAssetMovementSettings } from '@/modules/settings/use-asset-movement-settings';

interface UsePotentialMatchesReturn {
  /**
   * Runs the match, then refreshes the unmatched list.
   *
   * @returns whether events were matched, so the caller only announces a real change
   */
  confirmMatch: () => Promise<boolean>;
  /** True while a match is being written. */
  matchingLoading: Readonly<Ref<boolean>>;
  /** Restrict the search to assets the unmatched entry could plausibly pair with. */
  modelOnlyExpectedAssets: Ref<boolean>;
  /** The identifiers the user picked to match against. */
  modelSelectedMatchIds: Ref<number[]>;
  /** The search window in hours, as typed. */
  modelSearchTimeRange: Ref<string>;
  /** The amount tolerance as a percentage, as typed. */
  modelTolerancePercentage: Ref<string>;
  /** Candidate events for the current search, close matches first. */
  potentialMatches: Readonly<Ref<PotentialMatchRow[]>>;
  /** Message describing why the last search failed, if it did. */
  searchError: Readonly<Ref<string | undefined>>;
  /** True while candidates are being fetched. */
  searchLoading: Readonly<Ref<boolean>>;
  /** Fetches candidates for the current filters. */
  searchPotentialMatches: () => Promise<void>;
}

/**
 * Drives the potential-matches pane: the search filters, the candidates they return, and writing
 * the chosen match.
 *
 * @remarks
 * Searches whenever the group changes, resetting the filters to the flow's defaults first, so the
 * pane never shows one group's candidates against another's filters.
 *
 * @param movement - the unmatched group being matched
 * @param flow - the backend calls and defaults to use; omitted means asset movements
 * @returns the pane's bindings; the `model`-prefixed refs are the filter inputs
 */
export function usePotentialMatches(
  movement: MaybeRefOrGetter<UnmatchedEventGroup>,
  flow?: MaybeRefOrGetter<MatchingFlow | undefined>,
): UsePotentialMatchesReturn {
  const searchLoading = shallowRef<boolean>(false);
  const matchingLoading = shallowRef<boolean>(false);
  const searchError = ref<string>();
  const potentialMatches = ref<PotentialMatchRow[]>([]);

  const { t } = useI18n({ useScope: 'global' });
  const { matchAssetMovement, refreshUnmatchedAssetMovements } = useUnmatchedAssetMovements();
  const { fetchHistoryEvents } = useHistoryEventsApi();
  const { getAssetMovementMatches } = useAssetMovementMatchingApi();
  const { assetMovementAmountTolerance, assetMovementTimeRange } = useAssetMovementSettings();

  function getDefaultHourRange(): number {
    return (toValue(flow)?.defaultTimeRangeSeconds ?? get(assetMovementTimeRange)) / 3600;
  }

  function getDefaultTolerancePercentage(): string {
    return bigNumberify(toValue(flow)?.defaultTolerance ?? get(assetMovementAmountTolerance))
      .multipliedBy(100)
      .toString();
  }

  const modelSelectedMatchIds = ref<number[]>([]);
  const modelSearchTimeRange = ref<string>(getDefaultHourRange().toString());
  const modelOnlyExpectedAssets = shallowRef<boolean>(true);
  const modelTolerancePercentage = ref<string>(getDefaultTolerancePercentage());

  function percentageToDecimal(percentage: string): string {
    const value = parseNumericInput(percentage, bigNumberify(getDefaultTolerancePercentage()));
    return value.dividedBy(100).toString();
  }

  function transformToMatchRow(row: HistoryEventCollectionRow, isCloseMatch: boolean): PotentialMatchRow {
    const { entry, ...meta } = getEventEntryFromCollection(row);
    const eventEntry = { ...entry, ...meta };
    return {
      entry: eventEntry,
      identifier: eventEntry.identifier,
      isCloseMatch,
    };
  }

  async function searchPotentialMatches(): Promise<void> {
    set(searchError, undefined);
    set(potentialMatches, []);
    set(searchLoading, true);

    try {
      const hours = Number.parseInt(get(modelSearchTimeRange), 10) || getDefaultHourRange();
      const timeRangeInSeconds = hours * 60 * 60;

      const group = toValue(movement);
      const getSuggestions = toValue(flow)?.getSuggestions
        ?? (async (m: UnmatchedEventGroup, timeRange: number, onlyExpected: boolean, tolerance: string): Promise<MatchSuggestions> =>
          getAssetMovementMatches(m.groupIdentifier, timeRange, onlyExpected, tolerance));
      const suggestions = await getSuggestions(
        group,
        timeRangeInSeconds,
        get(modelOnlyExpectedAssets),
        percentageToDecimal(get(modelTolerancePercentage)),
      );
      const allIdentifiers = [...suggestions.closeMatches, ...suggestions.otherEvents];

      if (allIdentifiers.length === 0)
        return;

      const response = await fetchHistoryEvents({
        aggregateByGroupIds: false,
        identifiers: allIdentifiers.map(String),
        limit: -1,
        offset: 0,
      });

      const closeMatchSet = new Set(suggestions.closeMatches);
      const matches = response.entries
        .map(row => transformToMatchRow(row, closeMatchSet.has(getEventEntryFromCollection(row).entry.identifier)));

      const identifierOrderMap = new Map(allIdentifiers.map((id, index) => [id, index]));
      matches.sort((a, b) => {
        const orderA = identifierOrderMap.get(a.entry.identifier) ?? Number.MAX_SAFE_INTEGER;
        const orderB = identifierOrderMap.get(b.entry.identifier) ?? Number.MAX_SAFE_INTEGER;
        return orderA - orderB;
      });

      set(potentialMatches, matches);
    }
    catch (error) {
      logger.error('Failed to search potential matches:', error);
      set(searchError, t('asset_movement_matching.dialog.search_error', { error: getErrorMessage(error) }));
    }
    finally {
      set(searchLoading, false);
    }
  }

  async function confirmMatch(): Promise<boolean> {
    const matchIds = get(modelSelectedMatchIds);

    if (matchIds.length === 0)
      return false;

    set(matchingLoading, true);

    try {
      const group = toValue(movement);
      const unmatchedId = group.identifier ?? getEventEntryFromCollection(group.events).entry.identifier;

      if (!unmatchedId)
        return false;

      const selectedFlow = toValue(flow);
      const result = selectedFlow
        ? await selectedFlow.match(unmatchedId, matchIds)
        : await matchAssetMovement(unmatchedId, matchIds);

      if (!result.success)
        return false;

      if (selectedFlow)
        await selectedFlow.refresh(true);
      else
        await refreshUnmatchedAssetMovements(true);

      return true;
    }
    finally {
      set(matchingLoading, false);
    }
  }

  watchImmediate(() => toValue(movement), async () => {
    set(potentialMatches, []);
    set(modelSelectedMatchIds, []);
    set(modelSearchTimeRange, getDefaultHourRange().toString());
    set(modelOnlyExpectedAssets, true);
    set(modelTolerancePercentage, getDefaultTolerancePercentage());
    await searchPotentialMatches();
  });

  return {
    confirmMatch,
    matchingLoading: readonly(matchingLoading),
    modelOnlyExpectedAssets,
    modelSearchTimeRange,
    modelSelectedMatchIds,
    modelTolerancePercentage,
    potentialMatches: shallowReadonly(potentialMatches),
    searchError: readonly(searchError),
    searchLoading: readonly(searchLoading),
    searchPotentialMatches,
  };
}
