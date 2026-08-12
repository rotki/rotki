import type { Account, HistoryEventEntryType } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsFilters } from './use-history-events-filters';

let capturedRequestParams: ComputedRef<Partial<HistoryEventRequestPayload>> | undefined;
let capturedQueryParamsOnly: ComputedRef<Record<string, unknown>> | undefined;

interface ServerTableMockSource {
  values: ComputedRef<Record<string, unknown>>;
  to: 'request' | 'url' | 'both';
  skipEmpty?: boolean;
  isDefault?: boolean;
}

interface ServerTableMockOptions {
  params?: ServerTableMockSource[];
}

vi.mock('@/modules/core/table/use-server-table', () => ({
  routeWhen: (): { mode: 'route' } => ({ mode: 'route' }),
  useServerTable: vi.fn((options: ServerTableMockOptions) => {
    const sources = options.params ?? [];
    // The old `requestParams` bag is now the request-destination source that strips
    // empties; `queryParamsOnly` is the url-destination one.
    capturedRequestParams = sources.find(
      source => source.to === 'request' && !source.isDefault,
    )?.values;
    capturedQueryParamsOnly = sources.find(source => source.to === 'url')?.values;
    return {
      collection: ref({ data: [], found: 0, limit: 10, total: 0 }),
      filter: computed(() => ({})),
      isLoading: ref(false),
      markUserIntent: vi.fn(),
      pagination: computed(() => ({ limit: 10, limits: [10], page: 1, total: 0 })),
      refetch: vi.fn(),
      requestPayload: computed(() => ({})),
      setFilter: vi.fn(),
      setPage: vi.fn(),
      sort: computed(() => ({ column: undefined, direction: 'asc' as const })),
    };
  }),
}));

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: vi.fn(() => ({
    fetchHistoryEvents: vi.fn().mockResolvedValue({ data: [], found: 0, limit: 10, total: 0 }),
  })),
}));

const mockIsNavigating = ref<boolean>(false);
const mockClearAllHighlightTargets = vi.fn();

vi.mock('@/modules/history/events/use-history-event-navigation', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/history/events/use-history-event-navigation')>();
  return {
    ...actual,
    useHistoryEventNavigation: vi.fn(() => ({
      clearAllHighlightTargets: mockClearAllHighlightTargets,
      isNavigating: mockIsNavigating,
    })),
  };
});

vi.mock('@/modules/history/events/use-history-event-navigation-consumer', () => ({
  useHistoryEventNavigationConsumer: vi.fn(),
}));

// Store-backed too, and only consulted to expand an action verb into its type/subtype pair. One
// row is enough for the wiring this spec covers.
vi.mock('@/modules/history/events/action-picker/use-event-action-picker', () => ({
  useEventActionPicker: vi.fn(() => ({
    findRowByTypeSubtype: vi.fn(),
    rows: computed(() => [{
      combinations: [{ eventSubtype: 'fee', eventType: 'spend' }],
      direction: 'out',
      groupId: 'group',
      icon: 'lu-flame',
      label: 'Pay fee',
      verbKey: 'pay_fee',
    }]),
  })),
}));

interface DefaultOptions {
  options: {
    entryTypes: Ref<HistoryEventEntryType[] | undefined>;
    eventSubTypes: Ref<string[]>;
    eventTypes: Ref<string[]>;
    externalAccountFilter: Ref<Account[]>;
    fields: Ref<FieldDef[]>;
    filters: Ref<Filters>;
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
      // The view builds both and hands them in: the fields are what the table reads its url shape
      // off, and nothing here exercises the URL.
      fields: ref<FieldDef[]>([]),
      filters: ref<Filters>({}),
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
