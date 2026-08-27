import type { EffectScope, MaybeRef, Ref } from 'vue';
import type { RotkiApi } from '@/modules/core/api/rotki-api';
import type { Collection } from '@/modules/core/common/collection';
import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { LocationQuery } from '@/modules/core/table/route';
import { createMock } from '@test/utils/create-mock';
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
  api: createMock<RotkiApi>({
    cancelByTag: (tag: string): void => cancelByTagSpy(tag),
  }),
}));

vi.mock('vue-router', () => ({
  useRoute: useRouteMock,
  useRouter: useRouterMock,
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

/** A programmatic navigation, as a notification action or a deep link would make it. */
async function navigateTo(query: Record<string, unknown>): Promise<void> {
  await mockRouter.push({ query });
  await nextTick();
  await flushPromises();
}

/** The user editing the filter bar, as distinct from a value arriving by navigation. */
async function userSetsFilter<T extends object>(filter: Ref<T>, next: T): Promise<void> {
  set(filter, next);
  await nextTick();
  await flushPromises();
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

      await navigateTo({ txRefs: ['0xabc', '0xdef'] });

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

      await userSetsFilter(filter, { txRefs: ['0x123'] });

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

      await navigateTo({ txRefs: ['0xabc'] });
      savePersistedFilterSpy.mockClear();

      await userSetsFilter(filter, { txRefs: ['0xnew'] });

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      expect(getLastSavedQuery()).toHaveProperty('txRefs');
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

      await navigateTo({ txRefs: ['0xabc'] });
      savePersistedFilterSpy.mockClear();

      await userSetsFilter(filter, { txRefs: ['0xabc'], asset: 'ETH' });

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
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

      await navigateTo({ asset: 'ETH' });
      savePersistedFilterSpy.mockClear();

      await userSetsFilter(filter, { asset: 'ETH', txRefs: ['0x123'] });

      expect(savePersistedFilterSpy).toHaveBeenCalled();
      const savedQuery = getLastSavedQuery();
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

      await navigateTo({ txRefs: ['0xabc'], tempFilter: 'initial' });
      savePersistedFilterSpy.mockClear();

      await userSetsFilter(filter, { txRefs: ['0xnew'], tempFilter: 'changed' });

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

      await navigateTo({ txRefs: ['0xabc'], groupIdentifiers: 'group-1' });

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

      await userSetsFilter(filter, { txRefs: ['0x123'] });
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

      await mockRouter.push({ query: { txRefs: ['0xabc'] } });
      await nextTick();
      await flushPromises();

      await mockRouter.push({ query: {} });
      await nextTick();
      await flushPromises();
      savePersistedFilterSpy.mockClear();

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

    set(filter, { asset: 'ETH' });
    await nextTick();
    set(filter, { asset: 'BTC' });
    await nextTick();
    set(filter, { asset: 'USDT' });
    await nextTick();

    expect(requestFn).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();

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

    expect(cancelByTagSpy).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(250);
    await flushPromises();

    expect(cancelByTagSpy).toHaveBeenCalledWith('debounced-cancel-tag');
    expect(requestFn).toHaveBeenCalledTimes(1);

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

  it('should write the URL when the filter changes, since the internal page reset must not clear the pending user intent', async () => {
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

  it('should write the URL when a url-only source changes even though no fetch fires, since such values never reach the request payload', async () => {
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

  it('should infer the payload from fetch when no generics are passed, so a widening to any fails the assertions below rather than passing silently', async () => {
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

  it('should NOT reset the page when a url-only param changes, since the result set cannot move under a value the api never sees', async () => {
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

  it('should reset the page when a request-only param changes, earning no URL write because the reset carries no user intent', async () => {
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
