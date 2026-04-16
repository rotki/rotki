import type { MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEvent, HistoryEventRow } from '@/modules/history/events/schemas';
import { type Account, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { FilterBehaviour } from '@/modules/core/table/filtering';
import { type Filters, type Matcher, useHistoryEventFilter } from '@/modules/core/table/filters/use-events-filter';
import { type LocationQuery, RouterAccountsSchema } from '@/modules/core/table/route';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { useHistoryEvents } from '@/modules/history/events/use-history-events';

vi.mock('vue', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void): void => fn()),
  };
});

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

  beforeAll((): void => {
    setActivePinia(createPinia());
    const { connected } = storeToRefs(useMainStore());
    set(connected, true);
    fetchHistoryEvents = useHistoryEvents().fetchHistoryEvents;
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

    beforeEach((): void => {
      set(mainPage, true);
    });

    it('should initialize composable correctly', async () => {
      const { userAction, filters, sort, state, fetchData, isLoading } = usePaginationFilters<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: (): ReturnType<typeof useHistoryEventFilter> => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        onUpdateFilters,
        extraParams,
        requestParams,
      });

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(sort)).toStrictEqual({
        column: 'timestamp',
        direction: 'desc',
      });
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toBe(0);

      set(userAction, true);
      await nextTick();
      startPromise(fetchData());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(state).total).toBe(6);
    });

    it('should return correct types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: (): ReturnType<typeof useHistoryEventFilter> => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        onUpdateFilters,
        extraParams,
        requestParams,
      });

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<HistoryEventRow>>();
      expectTypeOf(get(state).data).toEqualTypeOf<HistoryEventRow[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    it('should modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sort: ['timestamp'], sortOrder: ['asc'] };

      const { isLoading, state, pageParams, sort } = usePaginationFilters<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: (): ReturnType<typeof useHistoryEventFilter> => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        onUpdateFilters,
        extraParams,
        requestParams,
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

      assertType<Collection<HistoryEventRow>>(get(state));
      assertType<HistoryEventRow[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(pageParams).locationLabels).toEqual(get(accounts)[0].address);
      expect(get(pageParams).location).toBe('ethereum');

      expect(get(state).data).toHaveLength(6);
      expect(get(state).found).toBe(6);
      expect(get(state).limit).toBe(-1);
      expect(get(state).total).toBe(6);

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

      const { isLoading, filters } = usePaginationFilters<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: (): ReturnType<typeof useHistoryEventFilter> => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        onUpdateFilters,
        extraParams,
        requestParams,
      });

      await router.push({
        query,
      });

      await nextTick();

      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      expect(get(filters).counterparties).toStrictEqual(get(protocols));
    });

    it('should handle exclusion filters', async () => {
      const fetchHistoryEvents = vi.fn();

      const { userAction, fetchData, isLoading, updateFilter } = usePaginationFilters<
        HistoryEvent,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: (): ReturnType<typeof useHistoryEventFilter> => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        onUpdateFilters,
        extraParams,
        requestParams,
      });

      updateFilter({
        location: 'protocols',
        entryTypes: ['!evm event'],
      });

      set(userAction, true);
      startPromise(fetchData());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      expect(fetchHistoryEvents).toHaveBeenCalledWith(
        expect.objectContaining({
          value: expect.objectContaining({
            entryTypes: {
              behaviour: FilterBehaviour.EXCLUDE,
              values: ['evm event'],
            },
          }),
        }),
      );
    });
  });
});
