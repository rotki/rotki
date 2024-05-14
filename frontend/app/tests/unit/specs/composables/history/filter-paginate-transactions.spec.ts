import { Blockchain } from '@rotki/common/lib/blockchain';
import flushPromises from 'flush-promises';
import { type LocationQuery, RouterAccountsSchema } from '@/types/route';
import { useMainStore } from '@/store/main';
import { FilterBehaviour } from '@/types/filtering';
import type { Filters, Matcher } from '@/composables/filters/events';
import type { Collection } from '@/types/collection';
import type {
  HistoryEvent,
  HistoryEventRequestPayload,
} from '@/types/history/events';
import type { Account } from '@rotki/common/src/account';
import type { MaybeRef } from '@vueuse/core';
import type Vue from 'vue';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue(
    reactive({
      query: {},
    }),
  ),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(({ query }) => {
      useRoute().query = query;
      return true;
    }),
  }),
}));

vi.mock('vue', async () => {
  const mod = await vi.importActual<Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: Function) => fn()),
  };
});

describe('composables::history/filter-paginate', () => {
  let fetchHistoryEvents: (
    payload: MaybeRef<HistoryEventRequestPayload>
  ) => Promise<Collection<HistoryEvent>>;
  const locationOverview: MaybeRef<string | null> = null;
  const mainPage: Ref<boolean> = ref(false);
  const protocols: Ref<string[]> = ref([]);
  const eventTypes: Ref<string[]> = ref([]);
  const eventSubTypes: Ref<string[]> = ref([]);
  const accounts: Ref<Account[]> = ref([
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
      accounts: get(accounts).map(
        account => `${account.address}#${account.chain}`,
      ),
    }));

    const customPageParams = computed<Partial<HistoryEventRequestPayload>>(
      () => ({
        protocols: get(protocols),
        eventTypes: get(eventTypes),
        eventSubtypes: get(eventSubTypes),
        location: 'ethereum',
        locationLabels: get(accounts)[0].address,
      }),
    );

    beforeEach(() => {
      set(mainPage, true);
    });

    it('initialize composable correctly', async () => {
      const {
        userAction,
        filters,
        sort,
        state,
        fetchData,
        applyRouteFilter,
        isLoading,
      } = usePaginationFilters<
        HistoryEvent,
        HistoryEventRequestPayload,
        HistoryEvent,
        Collection<HistoryEvent>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        fetchHistoryEvents,
        {
          onUpdateFilters,
          extraParams,
          customPageParams,
        },
      );

      expect(get(userAction)).toBe(true);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(sort)).toHaveLength(1);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      applyRouteFilter();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toEqual(6);
    });

    it('check the return types', () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        HistoryEvent,
        HistoryEventRequestPayload,
        HistoryEvent,
        Collection<HistoryEvent>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        fetchHistoryEvents,
        {
          onUpdateFilters,
          extraParams,
          customPageParams,
        },
      );

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<HistoryEvent>>();
      expectTypeOf(get(state).data).toEqualTypeOf<HistoryEvent[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    it('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortBy: ['timestamp'], sortDesc: ['false'] };

      const { isLoading, state, pageParams } = usePaginationFilters<
        HistoryEvent,
        HistoryEventRequestPayload,
        HistoryEvent,
        Collection<HistoryEvent>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        fetchHistoryEvents,
        {
          onUpdateFilters,
          extraParams,
          customPageParams,
        },
      );

      await router.push({
        query,
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(route.query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<HistoryEvent>>(get(state));
      assertType<HistoryEvent[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(pageParams).locationLabels).toEqual(get(accounts)[0].address);
      expect(get(pageParams).location).toEqual('ethereum');

      expect(get(state).data).toHaveLength(6);
      expect(get(state).found).toEqual(6);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(6);
    });

    it('add protocols to filters and expect the value to be set', async () => {
      set(protocols, ['gas', 'ens']);

      const query = {
        sortBy: ['timestamp'],
        sortDesc: ['false'],
        counterparties: get(protocols),
      };

      const { isLoading, filters } = usePaginationFilters<
        HistoryEvent,
        HistoryEventRequestPayload,
        HistoryEvent,
        Collection<HistoryEvent>,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
        fetchHistoryEvents,
        {
          onUpdateFilters,
          extraParams,
          customPageParams,
        },
      );

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

      const { userAction, fetchData, isLoading, updateFilter }
        = usePaginationFilters<
          HistoryEvent,
          HistoryEventRequestPayload,
          HistoryEvent,
          Collection<HistoryEvent>,
          Filters,
          Matcher
        >(
          locationOverview,
          mainPage,
          () => useHistoryEventFilter({ protocols: get(protocols).length > 0 }),
          fetchHistoryEvents,
          {
            onUpdateFilters,
            extraParams,
            customPageParams,
          },
        );

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
