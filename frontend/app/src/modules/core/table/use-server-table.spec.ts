import type { EffectScope, MaybeRef, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { LocationQuery } from '@/modules/core/table/route';
import flushPromises from 'flush-promises';
import { afterEach, beforeAll, beforeEach, describe, expect, expectTypeOf, it, type Mock, vi } from 'vitest';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { TableId } from '@/modules/core/table/use-remember-table-sorting';
import { useServerTable } from '@/modules/core/table/use-server-table';

interface RememberTableFilterOptions {
  enabled: Ref<boolean>;
  tableId: Ref<string>;
}

const {
  cancelByTagSpy,
  rememberTableFilterSpy,
  restorePersistedFilterSpy,
  savePersistedFilterSpy,
  useRouteMock,
  useRouterMock,
} = vi.hoisted(() => ({
  cancelByTagSpy: vi.fn<(tag: string) => void>(),
  rememberTableFilterSpy: vi.fn<(options: RememberTableFilterOptions) => void>(),
  restorePersistedFilterSpy: vi.fn<() => Promise<void>>(),
  savePersistedFilterSpy: vi.fn<(query: Record<string, unknown>) => void>(),
  useRouteMock: vi.fn(),
  useRouterMock: vi.fn(),
}));

vi.mock('@/modules/core/table/use-remember-table-filter', () => ({
  useRememberTableFilter: (options: RememberTableFilterOptions): {
    savePersistedFilter: typeof savePersistedFilterSpy;
    restorePersistedFilter: typeof restorePersistedFilterSpy;
  } => {
    rememberTableFilterSpy(options);
    return {
      savePersistedFilter: savePersistedFilterSpy,
      restorePersistedFilter: restorePersistedFilterSpy,
    };
  },
}));

function getLastPersistenceOptions(): RememberTableFilterOptions {
  return rememberTableFilterSpy.mock.calls.at(-1)![0];
}

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
  // The mocked push always resolves successfully, so no write is ever a failure.
  isNavigationFailure: vi.fn().mockReturnValue(false),
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

/** Payload shape used by the `params` precedence/destination tests. */
interface TestPayloadWithExtras extends PaginationRequestPayload<TestItem> {
  asset?: string;
  bothParam?: string;
  emptyArr?: string[];
  emptyStr?: string;
  filled?: string;
  requestParam?: string;
  urlParam?: string;
}

interface TestFilters extends MatchedKeywordWithBehaviour<string> {
  asset?: string;
  identifiers?: string;
  tempFilter?: string;
  txRefs?: string[];
}

function mockRequestData(): (payload: MaybeRef<TestPayload>) => Promise<Collection<TestItem>> {
  return vi.fn().mockResolvedValue({
    data: [],
    found: 0,
    limit: -1,
    total: 0,
    totalUsdValue: '0',
  });
}

/** Typed against the wider payload, so `TPayload` has something distinctive to infer. */
function mockRequestWithExtras(): (payload: MaybeRef<TestPayloadWithExtras>) => Promise<Collection<TestItem>> {
  return vi.fn().mockResolvedValue({
    data: [],
    found: 0,
    limit: -1,
    total: 0,
    totalUsdValue: '0',
  });
}

/**
 * The filter bag and the fields it is declared by. The url shape is derived from the fields, so a
 * table under test states its keys once, the same way a real one does.
 */
function createTestFilterOptions(): { fields: FieldDef[]; filters: Ref<TestFilters> } {
  return {
    fields: [
      toMatchFieldDef({ key: 'asset', label: 'Asset', multiple: false }),
      toMatchFieldDef({ key: 'identifiers', label: 'Identifiers', multiple: false }),
      toMatchFieldDef({ key: 'tempFilter', label: 'Temp filter', multiple: false }),
      toMatchFieldDef({ key: 'txRefs', label: 'Tx refs', multiple: true }),
    ],
    filters: ref<TestFilters>({}),
  };
}

function getLastSavedQuery(): Record<string, unknown> {
  const calls = savePersistedFilterSpy.mock.calls;
  return calls.at(-1)![0];
}

function getLastPushedQuery(): Record<string, unknown> {
  const calls = mockRouter.push.mock.calls;
  return calls.at(-1)![0].query;
}

function setupRouterMocks(): void {
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
}

describe('filter-persistence', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  describe('keys: never', () => {
    it('should strip never keys from the persisted filter on user action', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { identifiers: 'never', groupIdentifiers: 'never' }, tableId: TableId.HISTORY },
        params: [{
          values: computed(() => ({
            identifiers: 'some-id',
            groupIdentifiers: 'group-1,group-2',
          })),
          to: 'both',
        }],
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filter, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('identifiers');
      expect(savedQuery).not.toHaveProperty('groupIdentifiers');
      expect(savedQuery).toHaveProperty('asset', 'ETH');
      expect(savedQuery).toHaveProperty('limit');
    });

    it('should strip never keys even on programmatic navigation', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { identifiers: 'never' }, tableId: TableId.HISTORY },
        params: [{
          values: computed(() => ({ identifiers: 'some-id' })),
          to: 'both',
        }],
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

    it('should persist all keys when no key policy is given', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { tableId: TableId.HISTORY },
        params: [{
          values: computed(() => ({ identifiers: 'some-id' })),
          to: 'both',
        }],
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filter, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('identifiers');
      expect(savedQuery).toHaveProperty('asset');
    });

    it('should strip multiple never keys from different sources', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { identifiers: 'never', groupIdentifiers: 'never', duplicateHandlingStatus: 'never' }, tableId: TableId.HISTORY },
        params: [
          {
            values: computed(() => ({
              identifiers: 'id-1',
              groupIdentifiers: 'group-1',
            })),
            to: 'both',
          },
          {
            values: computed(() => ({ duplicateHandlingStatus: 'manual-review' })),
            to: 'url',
            skipEmpty: true,
          },
        ],
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filter, { asset: 'BTC' });
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

  describe('keys: untilChanged', () => {
    it('should strip transient keys when set from programmatic navigation', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
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
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User manually sets txRefs via filter UI (no prior navigation with txRefs)
      set(filter, { txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('txRefs');
    });

    it('should persist transient keys when user modifies the value after navigation', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate with txRefs
      await mockRouter.push({ query: { txRefs: ['0xabc'] } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User changes txRefs to a different value
      set(filter, { txRefs: ['0xnew'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      // Value changed from navigation value, so it should be persisted
      expect(savedQuery).toHaveProperty('txRefs');
    });

    it('should strip transient key when value still matches navigation value', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate with txRefs
      await mockRouter.push({ query: { txRefs: ['0xabc'] } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User changes a different filter, but txRefs stays the same
      set(filter, { txRefs: ['0xabc'], asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      // txRefs unchanged from navigation, so it is still stripped
      expect(savedQuery).not.toHaveProperty('txRefs');
      expect(savedQuery).toHaveProperty('asset');
    });

    it('should not strip transient keys when navigation had no transient values', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate without txRefs
      await mockRouter.push({ query: { asset: 'ETH' } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User adds txRefs manually
      set(filter, { asset: 'ETH', txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      // No transient values captured from navigation, so txRefs should persist
      expect(savedQuery).toHaveProperty('txRefs');
    });

    it('should strip multiple transient keys on programmatic navigation', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged', tempFilter: 'untilChanged' }, tableId: TableId.HISTORY },
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
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged', tempFilter: 'untilChanged' }, tableId: TableId.HISTORY },
      }))!;

      await nextTick();
      await flushPromises();

      // Navigate with transient keys
      await mockRouter.push({ query: { txRefs: ['0xabc'], tempFilter: 'initial' } });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User modifies both transient keys to new values
      set(filter, { txRefs: ['0xnew'], tempFilter: 'changed' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('txRefs');
      expect(savedQuery).toHaveProperty('tempFilter');
    });
  });

  describe('keys: never and untilChanged combined', () => {
    it('should always strip never keys and strip untilChanged keys on navigation', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { identifiers: 'never', groupIdentifiers: 'never', txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
        params: [{
          values: computed(() => ({ identifiers: 'id-1' })),
          to: 'both',
        }],
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

    it('should strip never keys but keep user-modified untilChanged keys', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { identifiers: 'never', txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
        params: [{
          values: computed(() => ({ identifiers: 'id-1' })),
          to: 'both',
        }],
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      // User manually adds txRefs (no prior navigation with txRefs)
      set(filter, { txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).not.toHaveProperty('identifiers');
      expect(savedQuery).toHaveProperty('txRefs');
    });
  });

  describe('no persist configured', () => {
    it('should not crash when persist is not set', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
      }))!;

      await nextTick();
      await flushPromises();

      set(filter, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
    });

    it('should persist full query without any key exclusion', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        params: [{
          values: computed(() => ({ identifiers: 'some-id' })),
          to: 'both',
        }],
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filter, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('identifiers');
      expect(savedQuery).toHaveProperty('asset');
    });
  });

  describe('persist with no key policies', () => {
    it('should persist the full query without modifications', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { tableId: TableId.HISTORY },
        params: [{
          values: computed(() => ({ identifiers: 'some-id' })),
          to: 'both',
        }],
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filter, { asset: 'ETH' });
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
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
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

      // User now sets txRefs, which should persist since tracking was reset
      set(filter, { txRefs: ['0x123'] });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('txRefs');
    });
  });

  describe('restorePersistedFilter', () => {
    it('should restore persisted filter when route query is empty', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { tableId: TableId.HISTORY },
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

      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { tableId: TableId.HISTORY },
      }));

      await nextTick();
      await flushPromises();

      expect(restorePersistedFilterSpy).not.toHaveBeenCalled();
    });
  });

  describe('edge cases', () => {
    it('should disable persistence when persist is omitted', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
      }));

      await nextTick();
      await flushPromises();

      // Absence is the off switch: there is no `enabled` flag left to disagree with it.
      expect(get(getLastPersistenceOptions().enabled)).toBe(false);
    });

    it('should enable persistence when persist is provided', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { tableId: TableId.HISTORY },
      }));

      await nextTick();
      await flushPromises();

      const options = getLastPersistenceOptions();
      expect(get(options.enabled)).toBe(true);
      expect(get(options.tableId)).toBe(TableId.HISTORY);
    });

    it('should handle never keys that are not in the query gracefully', async () => {
      const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { nonExistentKey: 'never', anotherMissing: 'never' }, tableId: TableId.HISTORY },
      }))!;

      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

      set(filter, { asset: 'ETH' });
      await nextTick();
      await flushPromises();

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
      expect(savedQuery).toHaveProperty('asset', 'ETH');
      expect(savedQuery).toHaveProperty('limit');
    });

    it('should handle untilChanged keys that are not in the navigation query', async () => {
      scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
        fetch: mockRequestData(),
        urlState: { mode: 'route' },
        ...createTestFilterOptions(),
        persist: { keys: { txRefs: 'untilChanged' }, tableId: TableId.HISTORY },
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

describe('request.debounce', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
    vi.useFakeTimers();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('should debounce refetch when request.debounce is set', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      request: { debounce: 200 },
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    requestFn.mockClear();

    // Rapid filter changes within the debounce window
    set(filter, { asset: 'ETH' });
    await nextTick();
    set(filter, { asset: 'BTC' });
    await nextTick();
    set(filter, { asset: 'USDT' });
    await nextTick();

    // Before debounce fires, no fetch should have been made
    expect(requestFn).not.toHaveBeenCalled();

    // Advance past the debounce window
    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();

    // Only one fetch should have been made (the final value)
    expect(requestFn).toHaveBeenCalledTimes(1);
  });

  it('should fetch immediately when request.debounce is unset', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    requestFn.mockClear();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    // Should fetch immediately without waiting for debounce
    expect(requestFn).toHaveBeenCalledTimes(1);
  });
});

describe('request.cancelTag', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should call api.cancelByTag before each refetch when request.cancelTag is set', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      request: { cancelTag: 'test-cancel-tag' },
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    cancelByTagSpy.mockClear();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(cancelByTagSpy).toHaveBeenCalledWith('test-cancel-tag');
  });

  it('should not call api.cancelByTag when request.cancelTag is not set', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    cancelByTagSpy.mockClear();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(cancelByTagSpy).not.toHaveBeenCalled();
  });

  it('should silently ignore RequestCancelledError in onError', async () => {
    const { RequestCancelledError: MockRequestCancelledError } = await import('@/modules/core/api');
    const requestFn = vi.fn().mockRejectedValue(new MockRequestCancelledError());

    scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      request: { cancelTag: 'test-cancel-tag' },
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }));

    await nextTick();
    await flushPromises();

    // Should not throw and collection should remain at default (empty collection)
    // The test passes if no unhandled error is thrown
  });

  it('should still fetch when url-only and request-only sources change together', async () => {
    vi.useFakeTimers();

    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const locationLabels = ref<string[]>([]);

    scope.run(() => useServerTable<TestItem, TestPayloadWithLabels, TestFilters>({
      fetch: requestFn,
      request: { debounce: 200 },
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [
        {
          values: computed<Partial<{ locationLabels: string[] }>>(() => {
            const labels = get(locationLabels);
            return labels.length > 0 ? { locationLabels: labels } : {};
          }),
          to: 'request',
          skipEmpty: true,
        },
        {
          values: computed(() => ({ locationLabels: get(locationLabels) })),
          to: 'url',
          skipEmpty: true,
        },
      ],
    }));

    await nextTick();
    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();
    requestFn.mockClear();

    // Simulate account filter change, which triggers both the request-only source
    // (which feeds into requestPayload) and the url-only source (which pushes the URL).
    // Without the self-write guard, the route push would re-apply url state, which
    // re-sets filters/pagination, causing requestPayload to recompute and overwrite
    // watchDebounced's old value, making it skip the fetch.
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

    scope.run(() => useServerTable<TestItem, TestPayloadWithLabels, TestFilters>({
      fetch: requestFn,
      request: { debounce: 200 },
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [
        {
          values: computed<Partial<{ locationLabels: string[] }>>(() => {
            const labels = get(locationLabels);
            return labels.length > 0 ? { locationLabels: labels } : {};
          }),
          to: 'request',
          skipEmpty: true,
        },
        {
          values: computed(() => ({ locationLabels: get(locationLabels) })),
          to: 'url',
          skipEmpty: true,
        },
      ],
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

  it('should apply url state on external navigation (browser back/forward)', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();

    // Simulate external navigation (browser back/forward) by directly changing the route.
    // This should apply filters from the route, unlike self-writes which skip applyUrlState.
    set(mockRoute, { query: { asset: 'ETH', limit: '10' } });
    await nextTick();
    await flushPromises();

    expect(get(filter)).toEqual(expect.objectContaining({ asset: 'ETH' }));
  });

  it('should cancel before fetching when combined with request.debounce', async () => {
    vi.useFakeTimers();

    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      request: { cancelTag: 'debounced-cancel-tag', debounce: 200 },
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    cancelByTagSpy.mockClear();
    requestFn.mockClear();

    set(filter, { asset: 'ETH' });
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

describe('sources precedence', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should let the filter override a base source', async () => {
    const { filter, requestPayload } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{
        values: computed(() => ({ asset: 'FROM_BASE' })),
        to: 'request',
        isDefault: true,
      }],
    }))!;

    await nextTick();
    await flushPromises();

    // No filter set yet, the base source supplies the value.
    expect(get(requestPayload).asset).toBe('FROM_BASE');

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(get(requestPayload).asset).toBe('ETH');
  });

  it('should let a non-base source override the filter', async () => {
    const { filter, requestPayload } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{
        values: computed(() => ({ asset: 'FROM_SOURCE' })),
        to: 'request',
      }],
    }))!;

    await nextTick();
    await flushPromises();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(get(requestPayload).asset).toBe('FROM_SOURCE');
  });

  it('should let array order decide between two non-base sources', async () => {
    const { requestPayload } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [
        { values: computed(() => ({ asset: 'FIRST' })), to: 'request' },
        { values: computed(() => ({ asset: 'SECOND' })), to: 'request' },
      ],
    }))!;

    await nextTick();
    await flushPromises();

    expect(get(requestPayload).asset).toBe('SECOND');
  });
});

describe('source destinations', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should route each destination to the right channel', async () => {
    const { filter, requestPayload } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [
        { values: computed(() => ({ requestParam: 'req' })), to: 'request' },
        { values: computed(() => ({ urlParam: 'url' })), to: 'url' },
        { values: computed(() => ({ bothParam: 'both' })), to: 'both' },
      ],
    }))!;

    await nextTick();
    await flushPromises();

    // A user filter change is what produces the URL write.
    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    const params = get(requestPayload);
    expect(params.requestParam).toBe('req');
    expect(params.bothParam).toBe('both');
    expect(params).not.toHaveProperty('urlParam');

    expect(mockRouter.push).toHaveBeenCalled();
    const pushedQuery = getLastPushedQuery();
    expect(pushedQuery).toHaveProperty('urlParam', 'url');
    expect(pushedQuery).toHaveProperty('bothParam', 'both');
    expect(pushedQuery).not.toHaveProperty('requestParam');
  });

  it('should write the URL when the filter changes', async () => {
    // Regression guard: the internal `setPage(1, 'programmatic')` fired by the
    // filter watcher must not clear the pending `user` provenance, otherwise no
    // URL write happens at all.
    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    mockRouter.push.mockClear();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(mockRouter.push).toHaveBeenCalled();
    expect(getLastPushedQuery()).toHaveProperty('asset', 'ETH');
  });

  it('should write the URL when a url-only source changes even though no fetch fires', async () => {
    // Was the `queryParamsOnly` watcher: url-only values never reach requestPayload,
    // so without a dedicated write the URL would go stale.
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });
    const urlOnly = ref<string>('');

    scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: requestFn,
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{
        values: computed(() => ({ urlParam: get(urlOnly) })),
        to: 'url',
        skipEmpty: true,
      }],
    }));

    await nextTick();
    await flushPromises();
    mockRouter.push.mockClear();
    requestFn.mockClear();

    set(urlOnly, 'value');
    await nextTick();
    await flushPromises();

    expect(mockRouter.push).toHaveBeenCalled();
    expect(getLastPushedQuery()).toHaveProperty('urlParam', 'value');
    expect(requestFn).not.toHaveBeenCalled();
  });

  it('should drop empty values with skipEmpty, and empty strings for the url', async () => {
    const { filter, requestPayload } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{
        values: computed(() => ({ emptyArr: [], emptyStr: '', filled: 'x' })),
        to: 'both',
        skipEmpty: true,
      }],
    }))!;

    await nextTick();
    await flushPromises();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    const params = get(requestPayload);
    expect(params).not.toHaveProperty('emptyArr');
    expect(params.filled).toBe('x');
    // For the request destination, empty strings survive (removeEmptyString is url-only).
    expect(params.emptyStr).toBe('');

    const pushedQuery = getLastPushedQuery();
    expect(pushedQuery).not.toHaveProperty('emptyArr');
    expect(pushedQuery).not.toHaveProperty('emptyStr');
    expect(pushedQuery).toHaveProperty('filled', 'x');
  });

  it('should keep empty values when skipEmpty is not set', async () => {
    const { requestPayload } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{
        values: computed(() => ({ emptyArr: [], emptyStr: '' })),
        to: 'request',
      }],
    }))!;

    await nextTick();
    await flushPromises();

    const params = get(requestPayload);
    expect(params.emptyArr).toEqual([]);
    expect(params.emptyStr).toBe('');
  });
});

describe('urlState modes', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should not watch the route nor write the URL when mode is none', async () => {
    const requestFn = vi.fn().mockResolvedValue({
      data: [],
      found: 0,
      limit: -1,
      total: 0,
    });

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      urlState: { mode: 'none' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();

    // A route change must not be observed at all.
    set(mockRoute, { query: { asset: 'ETH' } });
    await nextTick();
    await flushPromises();

    expect(get(filter)).toEqual({});
    expect(restorePersistedFilterSpy).not.toHaveBeenCalled();

    // A user filter change still fetches, but never touches the router.
    set(filter, { asset: 'BTC' });
    await nextTick();
    await flushPromises();

    expect(requestFn).toHaveBeenCalled();
    expect(mockRouter.push).not.toHaveBeenCalled();
  });

  it('should write to the passed ref instead of the router when mode is ref', async () => {
    const query = ref<LocationQuery>({});

    const { filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'ref', query },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    mockRouter.push.mockClear();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(get(query)).toHaveProperty('asset', 'ETH');
    expect(get(query)).toHaveProperty('limit');
    expect(mockRouter.push).not.toHaveBeenCalled();
  });
});

describe('sort.fallbackColumn', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should sort by timestamp when neither a default nor a fallback is given', async () => {
    const { requestPayload } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();

    expect(get(requestPayload).orderByAttributes).toEqual(['timestamp']);
  });

  it('should sort by the configured fallback column instead of timestamp', async () => {
    const { requestPayload } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      sort: { fallbackColumn: 'name' },
    }))!;

    await nextTick();
    await flushPromises();

    expect(get(requestPayload).orderByAttributes).toEqual(['name']);
  });

  it('should let an explicit default win over the fallback column', async () => {
    const { requestPayload } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      sort: { default: { column: 'id', direction: 'asc' }, fallbackColumn: 'name' },
    }))!;

    await nextTick();
    await flushPromises();

    expect(get(requestPayload).orderByAttributes).toEqual(['id']);
    expect(get(requestPayload).ascending).toEqual([true]);
  });
});

describe('error', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should expose the failure when the fetch rejects', async () => {
    const failure = new Error('request blew up');
    const requestFn = vi.fn().mockRejectedValue(failure);

    const { error, filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: requestFn,
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(requestFn).toHaveBeenCalled();
    expect(get(error)).toBe(failure);
  });

  it('should leave error unset while fetches succeed', async () => {
    const { error, filter } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(get(error)).toBeUndefined();
  });
});

describe('generic inference', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should infer the payload from fetch when no generics are passed', async () => {
    // No explicit generics: `TPayload` has to come from `fetch`. If it ever widens
    // to `any` the type assertions below fail rather than silently passing.
    const table = scope.run(() => useServerTable({
      fetch: mockRequestWithExtras(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{ values: computed(() => ({ asset: 'INFERRED' })), to: 'request' }],
    }))!;

    await nextTick();
    await flushPromises();

    const payload = get(table.requestPayload);

    expectTypeOf(payload).not.toBeAny();
    expectTypeOf(payload).toEqualTypeOf<TestPayloadWithExtras>();
    expectTypeOf(table.collection).toEqualTypeOf<Ref<Collection<TestItem>>>();
    expectTypeOf(table.filter.value).toEqualTypeOf<TestFilters>();

    expect(payload.asset).toBe('INFERRED');
    expect(payload).toHaveProperty('limit');
  });
});

describe('page reset', () => {
  let scope: EffectScope;

  beforeAll(() => {
    setActivePinia(createPinia());
  });

  beforeEach(() => {
    scope = effectScope();
    setupRouterMocks();
  });

  afterEach(async () => {
    scope.stop();
    await nextTick();
    vi.clearAllMocks();
  });

  it('should reset to page 1 when the filter changes', async () => {
    const { filter, pagination } = scope.run(() => useServerTable<TestItem, TestPayload, TestFilters>({
      fetch: mockRequestData(),
      ...createTestFilterOptions(),
    }))!;

    await nextTick();
    await flushPromises();
    set(pagination, { ...get(pagination), page: 5 });
    await nextTick();
    expect(get(pagination).page).toBe(5);

    set(filter, { asset: 'ETH' });
    await nextTick();
    await flushPromises();

    expect(get(pagination).page).toBe(1);
  });

  it('should NOT reset the page when a url-only param changes', async () => {
    // Url-only values never reach the api, so the result set cannot move under them
    // and the current page is still valid.
    const highlight = ref<string>('a');
    const { pagination } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestData(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{ values: computed(() => ({ urlParam: get(highlight) })), to: 'url' }],
    }))!;

    await nextTick();
    await flushPromises();
    set(pagination, { ...get(pagination), page: 5 });
    await nextTick();
    await flushPromises();
    expect(get(pagination).page).toBe(5);

    set(highlight, 'b');
    await nextTick();
    await flushPromises();

    expect(get(pagination).page).toBe(5);
  });

  it('should reset the page when a request-only param changes (8b)', async () => {
    // Request-only values reach the api, so the result set moves under them and the
    // current page can be invalid. Resetting carries no user intent, so no URL write is
    // earned: this is the parity fix for filters edited outside the TableFilter bar.
    const account = ref<string>('a');
    const { pagination } = scope.run(() => useServerTable<TestItem, TestPayloadWithExtras, TestFilters>({
      fetch: mockRequestWithExtras(),
      urlState: { mode: 'route' },
      ...createTestFilterOptions(),
      params: [{ skipEmpty: true, to: 'request', values: computed(() => ({ requestParam: get(account) })) }],
    }))!;

    await nextTick();
    await flushPromises();
    set(pagination, { ...get(pagination), page: 5 });
    await nextTick();
    await flushPromises();
    expect(get(pagination).page).toBe(5);

    set(account, 'b');
    await nextTick();
    await flushPromises();

    expect(get(pagination).page).toBe(1);
  });
});
