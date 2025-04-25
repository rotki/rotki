import type { Collection } from '@/types/collection';
import type { HistoryEvent, HistoryEventRequestPayload, HistoryEventRow } from '@/types/history/events';
import type { Account } from '@rotki/common/src/account';
import type { MaybeRef } from '@vueuse/core';
import type * as Vue from 'vue';
import { type Filters, type Matcher, useHistoryEventFilter } from '@/composables/filters/events';
import { useHistoryEvents } from '@/composables/history/events';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useMainStore } from '@/store/main';
import { FilterBehaviour } from '@/types/filtering';
import { type LocationQuery, RouterAccountsSchema } from '@/types/route';
import { Blockchain } from '@rotki/common';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeAll, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';

vi.mock('vue-router', async () => {
  const { ref } = await import('vue');
  const { set } = await import('@vueuse/core');
  const route = ref({
    query: {},
  });
  return {
    useRoute: vi.fn().mockReturnValue(route),
    useRouter: vi.fn().mockReturnValue({
      push: vi.fn(({ query }) => {
        set(route, { query });
        return true;
      }),
    }),
  };
});

vi.mock('vue', async () => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void) => fn()),
  };
});

describe('composables::history/filter-paginate', () => {
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

  beforeAll(() => {
    setActivePinia(createPinia());
    const { connected } = storeToRefs(useMainStore());
    set(connected, true);
    fetchHistoryEvents = useHistoryEvents().fetchHistoryEvents;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('components::history/trades/HistoryEventsView', () => {
    const onUpdateFilters = (query: LocationQuery) => {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      if (parsedAccounts.accounts)
        set(accounts, parsedAccounts.accounts);
    };

    const extraParams = computed(() => ({
      accounts: get(accounts).map(account => `${account.address}#${account.chain}`),
    }));

    const requestParams = computed<Partial<HistoryEventRequestPayload>>(() => ({
      protocols: get(protocols),
      eventTypes: get(eventTypes),
      eventSubtypes: get(eventSubTypes),
      location: 'ethereum',
      locationLabels: get(accounts)[0].address,
    }));

    beforeEach(() => {
      set(mainPage, true);
    });

    it('initialize composable correctly', async () => {
      const { userAction, filters, sort, state, fetchData, isLoading } = usePaginationFilters<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
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
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      await nextTick();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(state).total).toEqual(6);
    });

    it('check the return types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
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

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sort: ['timestamp'], sortOrder: ['asc'] };

      const { isLoading, state, pageParams, sort } = usePaginationFilters<
        HistoryEventRow,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
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
      expect(get(pageParams).location).toEqual('ethereum');

      expect(get(state).data).toHaveLength(6);
      expect(get(state).found).toEqual(6);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(6);

      expect(get(sort)).toStrictEqual({
        column: 'timestamp',
        direction: 'asc',
      });
    });

    it('add protocols to filters and expect the value to be set', async () => {
      set(protocols, ['ga s', 'ens']);

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
        filterSchema: () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        onUpdateFilters,
        extraParams,
        requestParams,
      });

      await router.push({
        query,
      });

      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      expect(get(filters).counterparties).toStrictEqual(get(protocols));
    });

    it('exclusion filters', async () => {
      const fetchHistoryEvents = vi.fn();

      const { userAction, fetchData, isLoading, updateFilter } = usePaginationFilters<
        HistoryEvent,
        HistoryEventRequestPayload,
        Filters,
        Matcher
      >(fetchHistoryEvents, {
        history: get(mainPage) ? 'router' : false,
        filterSchema: () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        onUpdateFilters,
        extraParams,
        requestParams,
      });

      updateFilter({
        location: 'protocols',
        entryTypes: ['!evm event'],
      });

      set(userAction, true);
      fetchData().catch(() => {});
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
