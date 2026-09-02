import type { MatchingFlow, MatchSuggestions, UnmatchedEventGroup } from './types';
import { createOnlineHistoryEvent } from '@test/utils/history-events';
import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, ref } from 'vue';
import { HistoryEventAccountingRuleStatus, type HistoryEventEntryWithMeta } from '@/modules/history/events/schemas';
import { usePotentialMatches } from './use-potential-matches';

const {
  assetMovementAmountTolerance,
  assetMovementTimeRange,
  fetchHistoryEvents,
  getAssetMovementMatches,
  matchAssetMovement,
  refreshUnmatchedAssetMovements,
} = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    assetMovementAmountTolerance: ref<string>('0.05'),
    assetMovementTimeRange: ref<number>(7200),
    fetchHistoryEvents: vi.fn(),
    getAssetMovementMatches: vi.fn(),
    matchAssetMovement: vi.fn(),
    refreshUnmatchedAssetMovements: vi.fn(),
  };
});

vi.mock('@/modules/history/events/use-unmatched-asset-movements', () => ({
  useUnmatchedAssetMovements: (): Record<string, unknown> => ({
    matchAssetMovement,
    refreshUnmatchedAssetMovements,
  }),
}));

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: (): Record<string, unknown> => ({ fetchHistoryEvents }),
}));

vi.mock('@/modules/history/api/events/use-asset-movement-matching-api', () => ({
  useAssetMovementMatchingApi: (): Record<string, unknown> => ({ getAssetMovementMatches }),
}));

vi.mock('@/modules/settings/use-asset-movement-settings', () => ({
  useAssetMovementSettings: (): Record<string, unknown> => ({
    assetMovementAmountTolerance,
    assetMovementTimeRange,
  }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
  setLevel: vi.fn(),
}));

let scope: ReturnType<typeof effectScope>;

function withMeta(identifier: number): HistoryEventEntryWithMeta {
  return {
    entry: createOnlineHistoryEvent({ identifier }),
    eventAccountingRuleStatus: HistoryEventAccountingRuleStatus.PROCESSED,
    ignoredInAccounting: false,
  };
}

function group(overrides: Partial<UnmatchedEventGroup> = {}): UnmatchedEventGroup {
  return {
    asset: 'ETH',
    events: withMeta(10),
    groupIdentifier: 'group-a',
    identifier: 42,
    ...overrides,
  };
}

function suggestions(closeMatches: number[], otherEvents: number[] = []): MatchSuggestions {
  return { closeMatches, otherEvents };
}

function matchingFlow(overrides: Partial<MatchingFlow> = {}): MatchingFlow {
  return {
    getSuggestions: vi.fn<MatchingFlow['getSuggestions']>(async () => Promise.resolve(suggestions([]))),
    match: vi.fn<MatchingFlow['match']>(async () => Promise.resolve({ success: true })),
    refresh: vi.fn<MatchingFlow['refresh']>(async () => Promise.resolve()),
    ...overrides,
  };
}

async function matches(
  movement: UnmatchedEventGroup | (() => UnmatchedEventGroup) = group(),
  flow?: MatchingFlow,
): Promise<ReturnType<typeof usePotentialMatches>> {
  scope = effectScope();
  const api = scope.run(() => usePotentialMatches(movement, flow))!;
  await flushPromises();
  return api;
}

describe('modules/history/events/matching/usePotentialMatches', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAssetMovementMatches.mockResolvedValue(suggestions([]));
    fetchHistoryEvents.mockResolvedValue({ entries: [], entriesFound: 0, entriesLimit: -1, entriesTotal: 0 });
    matchAssetMovement.mockResolvedValue({ success: true });
    refreshUnmatchedAssetMovements.mockResolvedValue(undefined);
    set(assetMovementTimeRange, 7200);
    set(assetMovementAmountTolerance, '0.05');
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the filters it starts from', () => {
    it('should pre-fill the settings when no flow overrides them', async () => {
      const { modelSearchTimeRange, modelTolerancePercentage } = await matches();

      expect(get(modelSearchTimeRange)).toBe('2');
      expect(get(modelTolerancePercentage)).toBe('5');
    });

    it('should prefer the flow defaults, so a bridge does not search on movement settings', async () => {
      const flow = matchingFlow({ defaultTimeRangeSeconds: 86400, defaultTolerance: '0.1' });

      const { modelSearchTimeRange, modelTolerancePercentage } = await matches(group(), flow);

      expect(get(modelSearchTimeRange)).toBe('24');
      expect(get(modelTolerancePercentage)).toBe('10');
    });
  });

  describe('searching', () => {
    it('should search as soon as it is given a group', async () => {
      await matches();

      expect(getAssetMovementMatches).toHaveBeenCalledExactlyOnceWith('group-a', 7200, true, '0.05');
    });

    it('should send the flow the group itself, not just its identifier', async () => {
      const flow = matchingFlow();
      const movement = group();

      await matches(movement, flow);

      expect(flow.getSuggestions).toHaveBeenCalledExactlyOnceWith(movement, 7200, true, '0.05');
      expect(getAssetMovementMatches).not.toHaveBeenCalled();
    });

    it('should convert the typed hours and percentage to the units the backend takes', async () => {
      const { modelSearchTimeRange, modelTolerancePercentage, searchPotentialMatches } = await matches();
      getAssetMovementMatches.mockClear();

      set(modelSearchTimeRange, '3');
      set(modelTolerancePercentage, '2.5');
      await searchPotentialMatches();

      expect(getAssetMovementMatches).toHaveBeenCalledWith('group-a', 10800, true, '0.025');
    });

    it('should fall back to the default window when the range is not a number', async () => {
      const { modelSearchTimeRange, searchPotentialMatches } = await matches();
      getAssetMovementMatches.mockClear();

      set(modelSearchTimeRange, '');
      await searchPotentialMatches();

      expect(getAssetMovementMatches).toHaveBeenCalledWith('group-a', 7200, true, '0.05');
    });

    it('should fall back to the default tolerance when it is not a number', async () => {
      const { modelTolerancePercentage, searchPotentialMatches } = await matches();
      getAssetMovementMatches.mockClear();

      set(modelTolerancePercentage, 'abc');
      await searchPotentialMatches();

      expect(getAssetMovementMatches).toHaveBeenCalledWith('group-a', 7200, true, '0.05');
    });

    it('should fetch nothing further when there is nothing to match against', async () => {
      const { potentialMatches } = await matches();

      expect(fetchHistoryEvents).not.toHaveBeenCalled();
      expect(get(potentialMatches)).toEqual([]);
    });

    it('should fetch every suggested event in one request', async () => {
      getAssetMovementMatches.mockResolvedValue(suggestions([2], [3, 4]));

      await matches();

      expect(fetchHistoryEvents).toHaveBeenCalledExactlyOnceWith({
        aggregateByGroupIds: false,
        identifiers: ['2', '3', '4'],
        limit: -1,
        offset: 0,
      });
    });

    it('should mark only the close matches as such', async () => {
      getAssetMovementMatches.mockResolvedValue(suggestions([2], [3]));
      fetchHistoryEvents.mockResolvedValue({ entries: [withMeta(2), withMeta(3)] });

      const { potentialMatches } = await matches();

      expect(get(potentialMatches).map(row => [row.identifier, row.isCloseMatch])).toEqual([[2, true], [3, false]]);
    });

    it('should keep the suggested order, which the fetch does not preserve', async () => {
      getAssetMovementMatches.mockResolvedValue(suggestions([7], [3, 5]));
      fetchHistoryEvents.mockResolvedValue({ entries: [withMeta(5), withMeta(3), withMeta(7)] });

      const { potentialMatches } = await matches();

      expect(get(potentialMatches).map(row => row.identifier)).toEqual([7, 3, 5]);
    });

    it('should push an event the backend returned unasked to the end, rather than dropping it', async () => {
      getAssetMovementMatches.mockResolvedValue(suggestions([7], [3]));
      fetchHistoryEvents.mockResolvedValue({ entries: [withMeta(99), withMeta(98), withMeta(3), withMeta(7)] });

      const { potentialMatches } = await matches();

      expect(get(potentialMatches).map(row => row.identifier)).toEqual([7, 3, 99, 98]);
    });

    it('should report the failure instead of leaving the pane spinning', async () => {
      getAssetMovementMatches.mockRejectedValue(new Error('backend down'));

      const { potentialMatches, searchError, searchLoading } = await matches();

      expect(get(searchError)).toContain('asset_movement_matching.dialog.search_error');
      expect(get(potentialMatches)).toEqual([]);
      expect(get(searchLoading)).toBe(false);
    });

    it('should clear a previous failure when searching again', async () => {
      getAssetMovementMatches.mockRejectedValueOnce(new Error('backend down'));
      const { searchError, searchPotentialMatches } = await matches();

      await searchPotentialMatches();

      expect(get(searchError)).toBeUndefined();
    });
  });

  describe('when the group changes', () => {
    it('should search the new group and drop the previous selection', async () => {
      const movement = ref<UnmatchedEventGroup>(group());
      const { modelSelectedMatchIds } = await matches(() => get(movement));
      set(modelSelectedMatchIds, [2]);

      set(movement, group({ groupIdentifier: 'group-b' }));
      await flushPromises();

      expect(get(modelSelectedMatchIds)).toEqual([]);
      expect(getAssetMovementMatches).toHaveBeenLastCalledWith('group-b', 7200, true, '0.05');
    });

    it('should drop the previous candidates, so one group never shows another\'s', async () => {
      getAssetMovementMatches.mockResolvedValueOnce(suggestions([2]));
      fetchHistoryEvents.mockResolvedValueOnce({ entries: [withMeta(2)] });
      const movement = ref<UnmatchedEventGroup>(group());
      const { potentialMatches } = await matches(() => get(movement));

      set(movement, group({ groupIdentifier: 'group-b' }));
      await flushPromises();

      expect(get(potentialMatches)).toEqual([]);
    });

    it('should reset filters the user had narrowed', async () => {
      const movement = ref<UnmatchedEventGroup>(group());
      const { modelOnlyExpectedAssets, modelSearchTimeRange } = await matches(() => get(movement));
      set(modelSearchTimeRange, '48');
      set(modelOnlyExpectedAssets, false);

      set(movement, group({ groupIdentifier: 'group-b' }));
      await flushPromises();

      expect(get(modelSearchTimeRange)).toBe('2');
      expect(get(modelOnlyExpectedAssets)).toBe(true);
    });
  });

  describe('confirming a match', () => {
    it('should match the selected events against the group', async () => {
      const { confirmMatch, modelSelectedMatchIds } = await matches();
      set(modelSelectedMatchIds, [2, 3]);

      const matched = await confirmMatch();

      expect(matchAssetMovement).toHaveBeenCalledExactlyOnceWith(42, [2, 3]);
      expect(refreshUnmatchedAssetMovements).toHaveBeenCalledExactlyOnceWith(true);
      expect(matched).toBe(true);
    });

    it('should route through the flow when there is one', async () => {
      const flow = matchingFlow();
      const { confirmMatch, modelSelectedMatchIds } = await matches(group(), flow);
      set(modelSelectedMatchIds, [2]);

      await confirmMatch();

      expect(flow.match).toHaveBeenCalledExactlyOnceWith(42, [2]);
      expect(flow.refresh).toHaveBeenCalledExactlyOnceWith(true);
      expect(matchAssetMovement).not.toHaveBeenCalled();
    });

    it('should fall back to the first event when the group names no identifier', async () => {
      const { confirmMatch, modelSelectedMatchIds } = await matches(group({ identifier: undefined }));
      set(modelSelectedMatchIds, [2]);

      await confirmMatch();

      expect(matchAssetMovement).toHaveBeenCalledWith(10, [2]);
    });

    it('should refuse to match a group whose event has no identifier yet', async () => {
      const events = { ...withMeta(0), entry: createOnlineHistoryEvent({ identifier: 0 }) };
      const { confirmMatch, modelSelectedMatchIds } = await matches(group({ events, identifier: undefined }));
      set(modelSelectedMatchIds, [2]);

      const matched = await confirmMatch();

      expect(matchAssetMovement).not.toHaveBeenCalled();
      expect(matched).toBe(false);
    });

    it('should do nothing when nothing is selected', async () => {
      const { confirmMatch } = await matches();

      const matched = await confirmMatch();

      expect(matchAssetMovement).not.toHaveBeenCalled();
      expect(matched).toBe(false);
    });

    it('should not refresh when the backend rejected the match', async () => {
      matchAssetMovement.mockResolvedValue({ message: 'nope', success: false });
      const { confirmMatch, modelSelectedMatchIds } = await matches();
      set(modelSelectedMatchIds, [2]);

      const matched = await confirmMatch();

      expect(refreshUnmatchedAssetMovements).not.toHaveBeenCalled();
      expect(matched).toBe(false);
    });

    it('should stop showing progress even when the match throws', async () => {
      matchAssetMovement.mockRejectedValue(new Error('boom'));
      const { confirmMatch, matchingLoading, modelSelectedMatchIds } = await matches();
      set(modelSelectedMatchIds, [2]);

      await expect(confirmMatch()).rejects.toThrow('boom');

      expect(get(matchingLoading)).toBe(false);
    });
  });
});
