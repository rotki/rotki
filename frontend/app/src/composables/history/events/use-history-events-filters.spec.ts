import type { Account, HistoryEventEntryType } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventsToggles } from '@/components/history/events/dialog-types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryEventsFilters } from './use-history-events-filters';

let capturedRequestParams: ComputedRef<Partial<HistoryEventRequestPayload>> | undefined;

vi.mock('@/composables/use-pagination-filter', () => ({
  usePaginationFilters: vi.fn((_requestFn: unknown, options: { requestParams?: ComputedRef<Partial<HistoryEventRequestPayload>> }) => {
    capturedRequestParams = options.requestParams;
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

vi.mock('@/composables/history/events/use-history-event-navigation', () => ({
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
  });

  afterEach(() => {
    vi.clearAllMocks();
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
});
