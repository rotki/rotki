import type { MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { ParamSource } from '@/modules/core/table/param-sources';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEvent, HistoryEventRow } from '@/modules/history/events/schemas';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { type Account, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { FilterBehaviours } from '@/modules/core/table/filtering';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { type LocationQuery, RouterAccountsSchema } from '@/modules/core/table/route';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

vi.mock('vue', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void): void => fn()),
  };
});

/**
 * The keys these tests exercise, declared the way the real fields declare them: the table reads the
 * url shape of its filter bag and the `{ behaviour, values }` wrapping off the fields it is given.
 * Only the handful in play here, so a test states what it depends on.
 */
const fields: FieldDef[] = [
  toMatchFieldDef({ key: 'asset', label: 'Asset', multiple: false }),
  toMatchFieldDef({ key: 'location', label: 'Location', multiple: false }),
  toMatchFieldDef({ key: 'counterparties', label: 'Protocol', multiple: true }),
  toMatchFieldDef({ allowExclusion: true, key: 'entryTypes', label: 'Type', multiple: true }),
];

describe('useHistoryEvents', () => {
  let fetchHistoryEvents: (payload: MaybeRef<HistoryEventRequestPayload>) => Promise<Collection<HistoryEventRow>>;
  const mainPage = ref<boolean>(false);
  const protocols = ref<string[]>([]);
  const eventTypes = ref<string[]>([]);
  const eventSubTypes = ref<string[]>([]);
  const accounts = ref<Account[]>([
    {
      address: '0x2F4c0f60f2116899FA6D4b9d8B979167CE963d25',
      chain: Blockchain.ETH,
    },
  ]);
  const router = useRouter();
  const route = useRoute();

  beforeEach(async (): Promise<void> => {
    // Fresh pinia per test plus a reset of every shared piece of mutable collection. The vue-router
    // mock route query is a module-level singleton mutated by useRouter().push, and the refs
    // below are mutated by individual tests (protocols, accounts via onUpdateFilters). Without
    // resetting them here, collection from one test leaks into whichever test runs next under
    // shuffle and breaks the default sort / filter assertions. A fresh useRouter() has its own
    // push mock, so this reset does not inflate any push-spy the tests assert on.
    setActivePinia(createPinia());
    const { connected } = storeToRefs(useMainStore());
    set(connected, true);
    fetchHistoryEvents = useHistoryEvents().fetchHistoryEvents;
    await useRouter().push({ query: {} });
    set(protocols, []);
    set(eventTypes, []);
    set(eventSubTypes, []);
    set(accounts, [
      {
        address: '0x2F4c0f60f2116899FA6D4b9d8B979167CE963d25',
        chain: Blockchain.ETH,
      },
    ]);
  });

  afterEach((): void => {
    vi.clearAllMocks();
  });

  describe('components::history/trades/HistoryEventsView', () => {
    const onUpdateFilters = (query: LocationQuery): void => {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      if (parsedAccounts.accounts)
        set(accounts, parsedAccounts.accounts);
    };

    const extraParams = computed(() => ({
      accounts: get(accounts).map((account): string => `${account.address}#${account.chain}`),
    }));

    const requestParams = computed<Partial<HistoryEventRequestPayload>>(() => ({
      protocols: get(protocols),
      eventTypes: get(eventTypes),
      eventSubtypes: get(eventSubTypes),
      location: 'ethereum',
      locationLabels: get(accounts)[0].address,
    }));

    // The old extraParams (request + url) and requestParams (request only,
    // non-empty) bags, in their original precedence order.
    const sources: ParamSource[] = [
      { fromQuery: onUpdateFilters, to: 'both', values: extraParams },
      { skipEmpty: true, to: 'request', values: requestParams },
    ];

    beforeEach((): void => {
      set(mainPage, true);
    });

    it('should initialize composable correctly', async () => {
      const { filter, sort, collection, refetch, isLoading } = useServerTable<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters
      >({
        fetch: fetchHistoryEvents,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        fields,
        params: sources,
      });
      expect(get(isLoading)).toBe(false);
      expect(get(filter)).to.toStrictEqual({});
      expect(get(sort)).toStrictEqual({
        column: 'timestamp',
        direction: 'desc',
      });
      expect(get(collection).data).toHaveLength(0);
      expect(get(collection).total).toBe(0);
      await nextTick();
      startPromise(refetch());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(collection).total).toBe(6);
    });

    it('should return correct types', () => {
      const { isLoading, collection, filter } = useServerTable<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters
      >({
        fetch: fetchHistoryEvents,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        params: sources,
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(collection)).toEqualTypeOf<Collection<HistoryEventRow>>();
      expectTypeOf(get(collection).data).toEqualTypeOf<HistoryEventRow[]>();
      expectTypeOf(get(collection).found).toEqualTypeOf<number>();
      expectTypeOf(get(filter)).toEqualTypeOf<Filters>();
    });

    it('should modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sort: ['timestamp'], sortOrder: ['asc'] };

      const { isLoading, collection, requestPayload, sort } = useServerTable<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters
      >({
        fetch: fetchHistoryEvents,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        fields,
        params: sources,
      });

      expect(get(sort)).toStrictEqual({
        column: 'timestamp',
        direction: 'desc',
      });

      await router.push({
        query,
      });

      await nextTick();

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(get(route).query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<HistoryEventRow>>(get(collection));
      assertType<HistoryEventRow[]>(get(collection).data);
      assertType<number>(get(collection).found);

      expect(get(requestPayload).locationLabels).toEqual(get(accounts)[0].address);
      expect(get(requestPayload).location).toBe('ethereum');

      expect(get(collection).data).toHaveLength(6);
      expect(get(collection).found).toBe(6);
      expect(get(collection).limit).toBe(-1);
      expect(get(collection).total).toBe(6);

      expect(get(sort)).toStrictEqual({
        column: 'timestamp',
        direction: 'asc',
      });
    });

    it('should add protocols to filters correctly', async () => {
      set(protocols, ['gas', 'ens']);

      const query = {
        sortBy: ['timestamp'],
        sortDesc: ['false'],
        counterparties: get(protocols),
      };

      const { isLoading, filter } = useServerTable<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters
      >({
        fetch: fetchHistoryEvents,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        fields,
        params: sources,
      });

      await router.push({
        query,
      });

      await nextTick();

      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      expect(get(filter).counterparties).toStrictEqual(get(protocols));
    });

    it('should handle exclusion filters', async () => {
      // The composable hands `requestData` the live requestPayload ref, so asserting
      // with toHaveBeenCalledWith would read the value at assertion time rather
      // than at call time. Snapshot each payload instead.
      const payloads: Partial<HistoryEventRequestPayload>[] = [];
      const fetchHistoryEvents = vi.fn(
        async (payload: MaybeRef<HistoryEventRequestPayload>): Promise<Collection<HistoryEvent>> => {
          payloads.push({ ...get(payload) });
          return { data: [], found: 0, limit: -1, total: 0 };
        },
      );

      const { markUserIntent, refetch, isLoading, setFilter } = useServerTable<
        HistoryEvent,
        HistoryEventRequestPayload,
        Filters
      >({
        fetch: fetchHistoryEvents,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        fields,
        params: sources,
      });

      setFilter({
        location: 'protocols',
        entryTypes: ['!evm event'],
      });

      // Load-bearing, not ceremony: this is what makes the filter reach the URL.
      // The route watcher applies url state asynchronously (it awaits
      // restorePersistedFilter first), so without a user-attributed write the route
      // query stays empty and that deferred applyUrlState clears the filter again
      // before the fetch under assertion.
      markUserIntent();
      startPromise(refetch());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      expect(payloads.at(-1)).toMatchObject({
        entryTypes: {
          behaviour: FilterBehaviours.EXCLUDE,
          values: ['evm event'],
        },
      });
    });
  });
});
