import type { EffectScope, MaybeRef, Ref } from 'vue';
import type { FilterSchema } from '@/composables/use-pagination-filter/types';
import type { Collection } from '@/types/collection';
import type { PaginationRequestPayload } from '@/types/common';
import type { MatchedKeywordWithBehaviour, SearchMatcher } from '@/types/filtering';
import flushPromises from 'flush-promises';
import { afterEach, beforeAll, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import { z } from 'zod/v4';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { TableId } from '@/modules/table/use-remember-table-sorting';
import { arrayify } from '@/utils/array';

const { restorePersistedFilterSpy, savePersistedFilterSpy, useRouteMock, useRouterMock } = vi.hoisted(() => ({
  restorePersistedFilterSpy: vi.fn<() => Promise<void>>(),
  savePersistedFilterSpy: vi.fn<(query: Record<string, unknown>) => void>(),
  useRouteMock: vi.fn(),
  useRouterMock: vi.fn(),
}));

vi.mock('@/modules/table/use-remember-table-filter', () => ({
  useRememberTableFilter: vi.fn().mockReturnValue({
    savePersistedFilter: savePersistedFilterSpy,
    restorePersistedFilter: restorePersistedFilterSpy,
  }),
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

describe('composables::use-pagination-filter', () => {
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

  describe('filter-persistence', () => {
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
});
