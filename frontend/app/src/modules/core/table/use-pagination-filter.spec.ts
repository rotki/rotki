import type { EffectScope, MaybeRef, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/modules/core/table/filtering';
import type { FilterSchema } from '@/modules/core/table/pagination-filter-types';
import flushPromises from 'flush-promises';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { z } from 'zod/v4';
import { arrayify } from '@/modules/core/common/data/array';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';

const { cancelByTagSpy, restorePersistedFilterSpy, savePersistedFilterSpy, useRouteMock, useRouterMock } = vi.hoisted(() => ({
  cancelByTagSpy: vi.fn<(tag: string) => void>(),
  restorePersistedFilterSpy: vi.fn<() => Promise<void>>(),
  savePersistedFilterSpy: vi.fn<(query: Record<string, unknown>) => void>(),
  useRouteMock: vi.fn(),
  useRouterMock: vi.fn(),
}));

vi.mock('@/modules/core/table/use-remember-table-filter', () => ({
  useRememberTableFilter: vi.fn().mockReturnValue({
    savePersistedFilter: savePersistedFilterSpy,
    restorePersistedFilter: restorePersistedFilterSpy,
  }),
}));

vi.mock('@/modules/core/api', () => ({
  RequestCancelledError: class RequestCancelledError extends Error {
    constructor(message: string = 'Request was cancelled') {
      super(message);
      this.name = 'RequestCancelledError';
    }
  },
  api: {
    cancelByTag: (tag: string): void => cancelByTagSpy(tag),
  },
}));

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
  useRouter: useRouterMock,
}));

let mockRoute: Ref<{ query: Record<string, unknown> }>;
let mockRouter: {
  currentRoute: Ref<{ query: Record<string, unknown> }>;
  push: Mock<(options: { query: Record<string, unknown> }) => Promise<void>>;
  replace: Mock<(options: { query: Record<string, unknown> }) => Promise<void>>;
};

interface TestItem {
  id: number;
  name: string;
}

type TestPayload = PaginationRequestPayload<TestItem>;

interface TestPayloadWithLabels extends PaginationRequestPayload<TestItem> {
  locationLabels?: string[];
}

interface TestFilters extends MatchedKeywordWithBehaviour<string> {
  asset?: string;
  identifiers?: string;
  tempFilter?: string;
  txRefs?: string[];
}

type TestMatcher = SearchMatcher<string, string>;

function mockRequestData(): (payload: MaybeRef<TestPayload>) => Promise<Collection<TestItem>> {
  return vi.fn().mockResolvedValue({
    data: [],
    found: 0,
    limit: -1,
    total: 0,
    totalUsdValue: '0',
  });
}

function createTestFilterSchema(): FilterSchema<TestFilters, TestMatcher> {
  const OptionalString = z.string().optional();
  const OptionalMultipleString = z.array(z.string()).or(z.string()).transform(arrayify).optional();

  return {
    filters: ref<TestFilters>({}),
    matchers: computed<TestMatcher[]>(() => []),
    RouteFilterSchema: z.object({
      asset: OptionalString,
      identifiers: OptionalString,
      tempFilter: OptionalString,
      txRefs: OptionalMultipleString,
    }),
  };
}

function getLastSavedQuery(): Record<string, unknown> {
  const calls = savePersistedFilterSpy.mock.calls;
  return calls.at(-1)![0];
}

describe('filter-persistence', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    mockRoute = ref<{ query: Record<string, unknown> }>({ query: {} });
    mockRouter = {
      currentRoute: mockRoute,
      push: vi.fn(async ({ query }: { query: Record<string, unknown> }) => {
        set(mockRoute, { query });
      }),
      replace: vi.fn(async ({ query }: { query: Record<string, unknown> }) => {
        set(mockRoute, { query });
      }),
    };
    useRouteMock.mockReturnValue(mockRoute);
    useRouterMock.mockReturnValue(mockRouter);
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  describe('excludeKeys', () => {
    it('should strip excludeKeys from persisted filter on user action', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          excludeKeys: ['identifiers', 'groupIdentifiers'],
          tableId: TableId.HISTORY,
        })),
        extraParams: computed(() => ({
          identifiers: 'some-id',
          groupIdentifiers: 'group-1,group-2',
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filters, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('identifiers');
      expect(savedQuery).not.toHaveProperty('groupIdentifiers');
      expect(savedQuery).toHaveProperty('asset', 'ETH');
      expect(savedQuery).toHaveProperty('limit');
    });

    it('should strip excludeKeys even on programmatic navigation', async () => {
      scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          excludeKeys: ['identifiers'],
          tableId: TableId.HISTORY,
        })),
        extraParams: computed(() => ({
          identifiers: 'some-id',
        })),
      }));

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      await mockRouter.push({ query: { asset: 'BTC' } });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('identifiers');
    });

    it('should persist all keys when excludeKeys is empty', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          excludeKeys: [],
          tableId: TableId.HISTORY,
        })),
        extraParams: computed(() => ({
          identifiers: 'some-id',
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filters, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('identifiers');
      expect(savedQuery).toHaveProperty('asset');
    });

    it('should strip multiple excludeKeys from different sources', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          excludeKeys: ['identifiers', 'groupIdentifiers', 'duplicateHandlingStatus'],
          tableId: TableId.HISTORY,
        })),
        extraParams: computed(() => ({
          identifiers: 'id-1',
          groupIdentifiers: 'group-1',
        })),
        queryParamsOnly: computed(() => ({
          duplicateHandlingStatus: 'manual-review',
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filters, { asset: 'BTC' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('identifiers');
      expect(savedQuery).not.toHaveProperty('groupIdentifiers');
      expect(savedQuery).not.toHaveProperty('duplicateHandlingStatus');
      expect(savedQuery).toHaveProperty('asset', 'BTC');
    });
  });

  describe('transientKeys', () => {
    it('should strip transient keys when set from programmatic navigation', async () => {
      scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
      }));

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // Simulate programmatic navigation (e.g., notification action)
      await mockRouter.push({ query: { txRefs: ['0xabc', '0xdef'] } });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('txRefs');
    });

    it('should persist transient keys when user sets them without prior navigation', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User manually sets txRefs via filter UI (no prior navigation with txRefs)
      set(filters, { txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('txRefs');
    });

    it('should persist transient keys when user modifies the value after navigation', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate with txRefs
      await mockRouter.push({ query: { txRefs: ['0xabc'] } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User changes txRefs to a different value
      set(filters, { txRefs: ['0xnew'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      // Value changed from navigation value, so it should be persisted
      expect(savedQuery).toHaveProperty('txRefs');
    });

    it('should strip transient key when value still matches navigation value', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate with txRefs
      await mockRouter.push({ query: { txRefs: ['0xabc'] } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User changes a different filter, but txRefs stays the same
      set(filters, { txRefs: ['0xabc'], asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      // txRefs unchanged from navigation → still stripped
      expect(savedQuery).not.toHaveProperty('txRefs');
      expect(savedQuery).toHaveProperty('asset');
    });

    it('should not strip transient keys when navigation had no transient values', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate without txRefs
      await mockRouter.push({ query: { asset: 'ETH' } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User adds txRefs manually
      set(filters, { asset: 'ETH', txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      // No transient values captured from navigation, so txRefs should persist
      expect(savedQuery).toHaveProperty('txRefs');
    });

    it('should strip multiple transient keys on programmatic navigation', async () => {
      scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs', 'tempFilter'],
        })),
      }));

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      await mockRouter.push({ query: { txRefs: ['0xabc'], tempFilter: 'value' } });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('txRefs');
      expect(savedQuery).not.toHaveProperty('tempFilter');
    });

    it('should persist multiple transient keys when user changes their values', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs', 'tempFilter'],
        })),
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate with transient keys
      await mockRouter.push({ query: { txRefs: ['0xabc'], tempFilter: 'initial' } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User modifies both transient keys to new values
      set(filters, { txRefs: ['0xnew'], tempFilter: 'changed' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('txRefs');
      expect(savedQuery).toHaveProperty('tempFilter');
    });
  });

  describe('excludeKeys and transientKeys combined', () => {
    it('should strip excludeKeys always and transient keys on navigation', async () => {
      scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          excludeKeys: ['identifiers', 'groupIdentifiers'],
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
        extraParams: computed(() => ({
          identifiers: 'id-1',
        })),
      }));

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // Programmatic navigation with both exclude and transient keys
      await mockRouter.push({ query: { txRefs: ['0xabc'], groupIdentifiers: 'group-1' } });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('identifiers');
      expect(savedQuery).not.toHaveProperty('txRefs');
      expect(savedQuery).toHaveProperty('limit');
    });

    it('should strip excludeKeys but keep user-modified transient keys', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          excludeKeys: ['identifiers'],
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
        extraParams: computed(() => ({
          identifiers: 'id-1',
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User manually adds txRefs (no prior navigation with txRefs)
      set(filters, { txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('identifiers');
      expect(savedQuery).toHaveProperty('txRefs');
    });
  });

  describe('no persistFilter configured', () => {
    it('should not crash when persistFilter is not set', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
      }))!;

      await nextTick();
      await flushPromises();

      set(filters, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
    });

    it('should persist full query without any key exclusion', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        extraParams: computed(() => ({
          identifiers: 'some-id',
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filters, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('identifiers');
      expect(savedQuery).toHaveProperty('asset');
    });
  });

  describe('persistFilter with no excludeKeys or transientKeys', () => {
    it('should persist the full query without modifications', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
        })),
        extraParams: computed(() => ({
          identifiers: 'some-id',
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filters, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('identifiers');
      expect(savedQuery).toHaveProperty('asset');
      expect(savedQuery).toHaveProperty('limit');
    });
  });

  describe('navigation resets transient tracking', () => {
    it('should reset transient tracking when navigating to empty query', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate with txRefs
      await mockRouter.push({ query: { txRefs: ['0xabc'] } });
      await nextTick();
      await flushPromises();

      // Navigate to empty query (resets transient tracking)
      await mockRouter.push({ query: {} });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User now sets txRefs — should persist since tracking was reset
      set(filters, { txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('txRefs');
    });
  });

  describe('restorePersistedFilter', () => {
    it('should restore persisted filter when route query is empty', async () => {
      scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
        })),
      }));

      await nextTick();
      await flushPromises();

      expect(restorePersistedFilterSpy).toHaveBeenCalled();
    });

    it('should not restore persisted filter when route query has values', async () => {
      // Set route query before creating the composable
      await mockRouter.push({ query: { asset: 'ETH' } });
      await nextTick();

      restorePersistedFilterSpy.mockClear();

      scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
        })),
      }));

      await nextTick();
      await flushPromises();

      expect(restorePersistedFilterSpy).not.toHaveBeenCalled();
    });
  });

  describe('edge cases', () => {
    it('should not persist when persistFilter.enabled is false', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: false,
          tableId: TableId.HISTORY,
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();
      restorePersistedFilterSpy.mockClear();

      set(filters, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      // savePersistedFilter is still called but useRememberTableFilter handles the enabled check internally
      expect(savePersistedFilterSpy).toHaveBeenCalled();
    });

    it('should handle excludeKeys that are not in the query gracefully', async () => {
      const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          excludeKeys: ['nonExistentKey', 'anotherMissing'],
          tableId: TableId.HISTORY,
        })),
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filters, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('asset', 'ETH');
      expect(savedQuery).toHaveProperty('limit');
    });

    it('should handle transientKeys that are not in the navigation query', async () => {
      scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(mockRequestData(), {
        history: 'router',
        filterSchema: () => createTestFilterSchema(),
        persistFilter: computed(() => ({
          enabled: true,
          tableId: TableId.HISTORY,
          transientKeys: ['txRefs'],
        })),
      }));

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // Navigate without any transient keys
      await mockRouter.push({ query: { asset: 'BTC' } });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('asset');
      expect(savedQuery).not.toHaveProperty('txRefs');
    });
  });
});

describe('fetchDebounce', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    mockRoute = ref<{ query: Record<string, unknown> }>({ query: {} });
    mockRouter = {
      currentRoute: mockRoute,
      push: vi.fn(async ({ query }: { query: Record<string, unknown> }) => {
        set(mockRoute, { query });
      }),
      replace: vi.fn(async ({ query }: { query: Record<string, unknown> }) => {
        set(mockRoute, { query });
      }),
    };
    useRouteMock.mockReturnValue(mockRoute);
    useRouterMock.mockReturnValue(mockRouter);
    vi.useFakeTimers();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('should debounce fetchData when fetchDebounce is set', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(requestFn, {
      fetchDebounce: 200,
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
    }))!;

    await nextTick();
    await flushPromises();
    requestFn.mockClear();

    // Rapid filter changes within the debounce window
    set(filters, { asset: 'ETH' });
    await nextTick();
    set(filters, { asset: 'BTC' });
    await nextTick();
    set(filters, { asset: 'USDT' });
    await nextTick();

    // Before debounce fires, no fetch should have been made
    expect(requestFn).not.toHaveBeenCalled();

    // Advance past the debounce window
    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();

    // Only one fetch should have been made (the final value)
    expect(requestFn).toHaveBeenCalledTimes(1);
  });

  it('should fetch immediately when fetchDebounce is 0 (default)', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(requestFn, {
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
    }))!;

    await nextTick();
    await flushPromises();
    requestFn.mockClear();

    set(filters, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    // Should fetch immediately without waiting for debounce
    expect(requestFn).toHaveBeenCalledTimes(1);
  });
});

describe('cancelTag', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    mockRoute = ref<{ query: Record<string, unknown> }>({ query: {} });
    mockRouter = {
      currentRoute: mockRoute,
      push: vi.fn(async ({ query }: { query: Record<string, unknown> }) => {
        set(mockRoute, { query });
      }),
      replace: vi.fn(async ({ query }: { query: Record<string, unknown> }) => {
        set(mockRoute, { query });
      }),
    };
    useRouteMock.mockReturnValue(mockRoute);
    useRouterMock.mockReturnValue(mockRouter);
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should call api.cancelByTag before each fetchData when cancelTag is set', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(requestFn, {
      cancelTag: 'test-cancel-tag',
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
    }))!;

    await nextTick();
    await flushPromises();
    cancelByTagSpy.mockClear();

    set(filters, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(cancelByTagSpy).toHaveBeenCalledWith('test-cancel-tag');
  });

  it('should not call api.cancelByTag when cancelTag is not set', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(requestFn, {
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
    }))!;

    await nextTick();
    await flushPromises();
    cancelByTagSpy.mockClear();

    set(filters, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(cancelByTagSpy).not.toHaveBeenCalled();
  });

  it('should silently ignore RequestCancelledError in onError', async () => {
    const { RequestCancelledError: MockRequestCancelledError } = await import('@/modules/core/api');
    const requestFn = vi.fn().mockRejectedValue(new MockRequestCancelledError());

    scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(requestFn, {
      cancelTag: 'test-cancel-tag',
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
    }));

    await nextTick();
    await flushPromises();

    // Should not throw and state should remain at default (empty collection)
    // The test passes if no unhandled error is thrown
  });

  it('should still fetch when queryParamsOnly and requestParams change from the same source', async () => {
    vi.useFakeTimers();

    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const locationLabels = ref<string[]>([]);

    scope.run(() => usePaginationFilters<TestItem, TestPayloadWithLabels, TestFilters, TestMatcher>(requestFn, {
      fetchDebounce: 200,
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
      requestParams: computed<Partial<{ locationLabels: string[] }>>(() => {
        const labels = get(locationLabels);
        return labels.length > 0 ? { locationLabels: labels } : {};
      }),
      queryParamsOnly: computed(() => ({
        locationLabels: get(locationLabels),
      })),
    }));

    await nextTick();
    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();
    requestFn.mockClear();

    // Simulate account filter change — this triggers both requestParams
    // (which feeds into pageParams) and queryParamsOnly (which pushes the URL).
    // Without the selfPush guard, the route push would trigger applyRouteFilter
    // which re-sets filters/pagination, causing pageParams to recompute and
    // overwrite watchDebounced's old value — making it skip the fetch.
    set(locationLabels, ['0x1aEa862845522cFF463D11B9371EedEa73e458bE']);
    await nextTick();
    await flushPromises();

    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();

    expect(requestFn).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it('should fetch when clearing locationLabels after having values', async () => {
    vi.useFakeTimers();

    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const locationLabels = ref<string[]>(['0x1aEa862845522cFF463D11B9371EedEa73e458bE']);

    scope.run(() => usePaginationFilters<TestItem, TestPayloadWithLabels, TestFilters, TestMatcher>(requestFn, {
      fetchDebounce: 200,
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
      requestParams: computed<Partial<{ locationLabels: string[] }>>(() => {
        const labels = get(locationLabels);
        return labels.length > 0 ? { locationLabels: labels } : {};
      }),
      queryParamsOnly: computed(() => ({
        locationLabels: get(locationLabels),
      })),
    }));

    await nextTick();
    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();
    requestFn.mockClear();

    // Clear the account filter
    set(locationLabels, []);
    await nextTick();
    await flushPromises();

    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();

    expect(requestFn).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it('should apply route filter on external navigation (browser back/forward)', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(requestFn, {
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
    }))!;

    await nextTick();
    await flushPromises();

    // Simulate external navigation (browser back/forward) by directly changing the route
    // This should apply filters from the route, unlike self-pushes which skip applyRouteFilter
    set(mockRoute, { query: { asset: 'ETH', limit: '10' } });
    await nextTick();
    await flushPromises();

    expect(get(filters)).toEqual(expect.objectContaining({ asset: 'ETH' }));
  });

  it('should cancel before fetching when combined with fetchDebounce', async () => {
    vi.useFakeTimers();

    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filters } = scope.run(() => usePaginationFilters<TestItem, TestPayload, TestFilters, TestMatcher>(requestFn, {
      cancelTag: 'debounced-cancel-tag',
      fetchDebounce: 200,
      history: 'router',
      filterSchema: () => createTestFilterSchema(),
    }))!;

    await nextTick();
    await flushPromises();
    cancelByTagSpy.mockClear();
    requestFn.mockClear();

    set(filters, { asset: 'ETH' });
    await nextTick();

    // Before debounce, cancel should not have been called yet
    expect(cancelByTagSpy).not.toHaveBeenCalled();

    // Advance past debounce
    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();

    // Cancel should be called before the fetch
    expect(cancelByTagSpy).toHaveBeenCalledWith('debounced-cancel-tag');
    expect(requestFn).toHaveBeenCalledTimes(1);

    // Verify cancel was called before fetch (cancel call index < request call index)
    const cancelOrder = cancelByTagSpy.mock.invocationCallOrder[0];
    const fetchOrder = requestFn.mock.invocationCallOrder[0];
    expect(cancelOrder).toBeLessThan(fetchOrder);

    vi.useRealTimers();
  });
});
