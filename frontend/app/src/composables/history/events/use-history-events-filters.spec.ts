import type { Account, HistoryEventEntryType } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventsToggles } from '@/components/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsFilters } from './use-history-events-filters';

let capturedRequestParams: ComputedRef<Partial<HistoryEventRequestPayload>> | undefined;
let capturedQueryParamsOnly: ComputedRef<Record<string, unknown>> | undefined;

interface PaginationMockOptions {
  requestParams?: ComputedRef<Partial<HistoryEventRequestPayload>>;
  queryParamsOnly?: ComputedRef<Record<string, unknown>>;
}

vi.mock('@/composables/use-pagination-filter', () => ({
  usePaginationFilters: vi.fn((_requestFn: unknown, options: PaginationMockOptions) => {
    capturedRequestParams = options.requestParams;
    capturedQueryParamsOnly = options.queryParamsOnly;
    return {
      fetchData: vi.fn(),
      filters: computed(() => ({})),
      isLoading: ref(false),
      matchers: computed(() => []),
      pageParams: computed(() => ({})),
      pagination: computed(() => ({ limit: 10, limits: [10], page: 1, total: 0 })),
      setPage: vi.fn(),
      sort: computed(() => ({ column: undefined, direction: 'asc' as const })),
      state: ref({ data: [], found: 0, limit: 10, total: 0 }),
      updateFilter: vi.fn(),
      userAction: ref(false),
    };
  }),
}));

vi.mock('@/composables/history/events', () => ({
  useHistoryEvents: vi.fn(() => ({
    fetchHistoryEvents: vi.fn().mockResolvedValue({ data: [], found: 0, limit: 10, total: 0 }),
  })),
}));

const mockIsNavigating = ref<boolean>(false);
const mockClearAllHighlightTargets = vi.fn();

vi.mock('@/composables/history/events/use-history-event-navigation', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/history/events/use-history-event-navigation')>();
  return {
    ...actual,
    useHistoryEventNavigation: vi.fn(() => ({
      clearAllHighlightTargets: mockClearAllHighlightTargets,
      isNavigating: mockIsNavigating,
    })),
  };
});

vi.mock('@/composables/history/events/use-history-event-navigation-consumer', () => ({
  useHistoryEventNavigationConsumer: vi.fn(),
}));

interface DefaultOptions {
  options: {
    entryTypes: Ref<HistoryEventEntryType[] | undefined>;
    eventSubTypes: Ref<string[]>;
    eventTypes: Ref<string[]>;
    externalAccountFilter: Ref<Account[]>;
    location: Ref<string | undefined>;
    mainPage: Ref<boolean>;
    period: Ref<undefined>;
    protocols: Ref<string[]>;
    useExternalAccountFilter: Ref<boolean | undefined>;
    validators: Ref<number[] | undefined>;
  };
  toggles: Ref<HistoryEventsToggles>;
  locationRef: Ref<string | undefined>;
}

function createDefaultOptions(locationValue?: string): DefaultOptions {
  const locationRef = ref<string | undefined>(locationValue);
  const toggles = ref<HistoryEventsToggles>({
    matchExactEvents: false,
    showIgnoredAssets: false,
    stateMarkers: [],
  });
  return {
    locationRef,
    options: {
      entryTypes: ref(undefined),
      eventSubTypes: ref<string[]>([]),
      eventTypes: ref<string[]>([]),
      externalAccountFilter: ref([]),
      location: locationRef,
      mainPage: ref(false),
      period: ref(undefined),
      protocols: ref<string[]>([]),
      useExternalAccountFilter: ref(undefined),
      validators: ref(undefined),
    },
    toggles,
  };
}

describe('useHistoryEventsFilters', () => {
  beforeEach(() => {
    capturedRequestParams = undefined;
    capturedQueryParamsOnly = undefined;
  });

  afterEach(async () => {
    const router = useRouter();
    await router.push({ query: {} });
    set(mockIsNavigating, false);
    vi.clearAllMocks();
  });

  describe('usedLocationLabels', () => {
    it('should use local locationLabels when useExternalAccountFilter is undefined', () => {
      const { options, toggles } = createDefaultOptions();
      const { onLocationLabelsChanged, usedLocationLabels } = useHistoryEventsFilters(options, toggles);

      onLocationLabelsChanged(['0xABC']);

      expect(get(usedLocationLabels)).toEqual(['0xABC']);
    });

    it('should use local locationLabels when useExternalAccountFilter is false', () => {
      const { options, toggles } = createDefaultOptions();
      set(options.useExternalAccountFilter, false);
      const { onLocationLabelsChanged, usedLocationLabels } = useHistoryEventsFilters(options, toggles);

      onLocationLabelsChanged(['0xABC']);

      expect(get(usedLocationLabels)).toEqual(['0xABC']);
    });

    it('should use external account filter when useExternalAccountFilter is true', () => {
      const { options, toggles } = createDefaultOptions();
      set(options.useExternalAccountFilter, true);
      set(options.externalAccountFilter, [{ address: '0xDEF', chain: 'eth' }]);
      const { usedLocationLabels } = useHistoryEventsFilters(options, toggles);

      expect(get(usedLocationLabels)).toEqual(['0xDEF']);
    });

    it('should reactively update when locationLabels change', async () => {
      const { options, toggles } = createDefaultOptions();
      const { onLocationLabelsChanged, usedLocationLabels } = useHistoryEventsFilters(options, toggles);

      expect(get(usedLocationLabels)).toEqual([]);

      onLocationLabelsChanged(['0xABC']);
      await nextTick();

      expect(get(usedLocationLabels)).toEqual(['0xABC']);

      onLocationLabelsChanged(['0xABC', '0xDEF']);
      await nextTick();

      expect(get(usedLocationLabels)).toEqual(['0xABC', '0xDEF']);

      onLocationLabelsChanged([]);
      await nextTick();

      expect(get(usedLocationLabels)).toEqual([]);
    });

    it('should include locationLabels in requestParams when set', async () => {
      const { options, toggles } = createDefaultOptions();
      const { onLocationLabelsChanged } = useHistoryEventsFilters(options, toggles);

      onLocationLabelsChanged(['0xABC']);
      await nextTick();

      expect(capturedRequestParams).toBeDefined();
      expect(get(capturedRequestParams!).locationLabels).toEqual(['0xABC']);
    });

    it('should not include locationLabels in requestParams when empty', () => {
      const { options, toggles } = createDefaultOptions();
      useHistoryEventsFilters(options, toggles);

      expect(capturedRequestParams).toBeDefined();
      expect(get(capturedRequestParams!).locationLabels).toBeUndefined();
    });
  });

  describe('requestParams location', () => {
    it('should include location in requestParams when location prop is set', () => {
      const { options, toggles } = createDefaultOptions('ethereum');

      useHistoryEventsFilters(options, toggles);

      expect(capturedRequestParams).toBeDefined();
      const params = get(capturedRequestParams!);
      expect(params.location).toBe('ethereum');
    });

    it('should not include location in requestParams when location prop is undefined', () => {
      const { options, toggles } = createDefaultOptions(undefined);

      useHistoryEventsFilters(options, toggles);

      expect(capturedRequestParams).toBeDefined();
      const params = get(capturedRequestParams!);
      expect(params.location).toBeUndefined();
    });

    it('should reactively update requestParams when location prop changes', async () => {
      const { locationRef, options, toggles } = createDefaultOptions('ethereum');

      useHistoryEventsFilters(options, toggles);

      expect(get(capturedRequestParams!).location).toBe('ethereum');

      set(locationRef, 'optimism');
      await nextTick();

      expect(get(capturedRequestParams!).location).toBe('optimism');
    });

    it('should convert location to snake_case in requestParams', () => {
      const { options, toggles } = createDefaultOptions('binanceus');

      useHistoryEventsFilters(options, toggles);

      expect(capturedRequestParams).toBeDefined();
      const params = get(capturedRequestParams!);
      expect(params.location).toBe('binanceus');
    });
  });

  describe('highlight preservation', () => {
    it('should include highlight params in queryParamsOnly when route has highlights', async () => {
      const router = useRouter();
      await router.push({ query: { highlightedAssetMovement: '123' } });

      const { options, toggles } = createDefaultOptions();
      useHistoryEventsFilters(options, toggles);

      expect(capturedQueryParamsOnly).toBeDefined();
      const params = get(capturedQueryParamsOnly!);
      expect(params.highlightedAssetMovement).toBe('123');
    });

    it('should return highlighted identifiers from route query', async () => {
      const router = useRouter();
      await router.push({ query: { highlightedAssetMovement: '42', highlightedPotentialMatch: '99' } });

      const { options, toggles } = createDefaultOptions();
      const { highlightedIdentifiers } = useHistoryEventsFilters(options, toggles);

      expect(get(highlightedIdentifiers)).toEqual(['42', '99']);
    });

    it('should return correct highlight types from route query', async () => {
      const router = useRouter();
      await router.push({ query: { highlightedAssetMovement: '10', highlightedNegativeBalanceEvent: '20' } });

      const { options, toggles } = createDefaultOptions();
      const { highlightTypes } = useHistoryEventsFilters(options, toggles);

      const types = get(highlightTypes);
      expect(types['10']).toBe('warning');
      expect(types['20']).toBe('error');
    });

    it('should return highlighted group identifier for internal tx conflicts', async () => {
      const router = useRouter();
      await router.push({ query: { highlightedInternalTxConflict: '0xabc' } });

      const { options, toggles } = createDefaultOptions();
      const { highlightedGroupIdentifier, highlightTypes } = useHistoryEventsFilters(options, toggles);

      expect(get(highlightedGroupIdentifier)).toBe('0xabc');
      expect(get(highlightTypes)['group:0xabc']).toBe('warning');
    });

    it('should preserve highlights when navigation system is active', async () => {
      const router = useRouter();

      // Simulate navigation system pushing route with highlights (isNavigating is true)
      set(mockIsNavigating, true);
      await router.push({ query: { highlightedAssetMovement: '123', page: '5' } });

      const { options, toggles } = createDefaultOptions();
      useHistoryEventsFilters(options, toggles);
      await nextTick();

      // Highlights should be preserved because isNavigating is true
      expect(get(capturedQueryParamsOnly!)?.highlightedAssetMovement).toBe('123');
      expect(mockClearAllHighlightTargets).not.toHaveBeenCalled();
    });

    it('should not include highlight keys in queryParamsOnly when no highlights are active', () => {
      const { options, toggles } = createDefaultOptions();
      useHistoryEventsFilters(options, toggles);

      expect(capturedQueryParamsOnly).toBeDefined();
      const params = get(capturedQueryParamsOnly!);
      expect(params).not.toHaveProperty('highlightedAssetMovement');
      expect(params).not.toHaveProperty('highlightedInternalTxConflict');
      expect(params).not.toHaveProperty('highlightedPotentialMatch');
      expect(params).not.toHaveProperty('highlightedNegativeBalanceEvent');
    });
  });
});
