import { Blockchain } from '@rotki/common/lib/blockchain';
import flushPromises from 'flush-promises';
import { type ComputedRef, type Ref } from 'vue';
import { RouterAccountsSchema } from '@/types/route';
import type { Filters, Matcher } from '@/composables/filters/transactions';
import type { Collection } from '@/types/collection';
import type {
  EthTransaction,
  EthTransactionEntry,
  EvmChainAddress,
  TransactionRequestPayload
} from '@/types/history/tx';
import type { LocationQuery } from '@/types/route';
import type {
  HistoryEventSubType,
  HistoryEventType,
  TransactionEventProtocol
} from '@rotki/common/lib/history/tx-events';
import type { GeneralAccount } from '@rotki/common/src/account';
import type { MaybeRef } from '@vueuse/shared';
import type Vue from 'vue';

vi.mock('vue-router/composables', () => ({
  useRoute: vi.fn().mockReturnValue(
    reactive({
      query: {}
    })
  ),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(({ query }) => {
      useRoute().query = query;
      return true;
    })
  })
}));

vi.mock('vue', async () => {
  const mod = await vi.importActual<Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn()
  };
});

describe('composables::history/filter-paginate', () => {
  let fetchTransactions: (
    payload: MaybeRef<TransactionRequestPayload>
  ) => Promise<Collection<EthTransactionEntry>>;
  const locationOverview: MaybeRef<string | null> = null;
  const mainPage: Ref<boolean> = ref(false);
  const protocols: Ref<TransactionEventProtocol[]> = ref([]);
  const eventTypes: Ref<HistoryEventType[]> = ref([]);
  const eventSubTypes: Ref<HistoryEventSubType[]> = ref([]);
  const accounts: Ref<GeneralAccount[]> = ref([
    {
      address: '0xa13A1BaF456e2B750a87B9e1987d1387CfdC05f6',
      chain: Blockchain.OPTIMISM,
      label: '',
      tags: []
    }
  ]);
  const router = useRouter();
  const route = useRoute();

  const filteredAccounts: ComputedRef<EvmChainAddress[]> = computed(() => [
    {
      address: '0xa13A1BaF456e2B750a87B9e1987d1387CfdC05f6',
      evmChain: 'optimism'
    }
  ]);

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchTransactions = useTransactions().fetchTransactions;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('components::history/trades/TransactionContent', () => {
    const onUpdateFilters = (query: LocationQuery) => {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      if (parsedAccounts.accounts) {
        set(accounts, parsedAccounts.accounts);
      }
    };

    const extraParams = computed(() => ({
      accounts: get(accounts).map(
        account => `${account.address}#${account.chain}`
      )
    }));

    const customPageParams = computed<Partial<TransactionRequestPayload>>(
      () => ({
        protocols: get(protocols),
        eventTypes: get(eventTypes),
        eventSubtypes: get(eventSubTypes),
        accounts: get(filteredAccounts)
      })
    );

    beforeEach(() => {
      set(mainPage, true);
    });

    test('initialize composable correctly', async () => {
      const {
        userAction,
        filters,
        options,
        state,
        fetchData,
        applyRouteFilter,
        isLoading
      } = useHistoryPaginationFilter<
        EthTransaction,
        TransactionRequestPayload,
        EthTransactionEntry,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        () => useTransactionFilter(get(protocols).length > 0),
        fetchTransactions,
        {
          onUpdateFilters,
          extraParams,
          customPageParams
        }
      );

      expect(get(userAction)).toBe(false);
      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(options).sortBy).toHaveLength(1);
      expect(get(options).sortDesc).toHaveLength(1);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toEqual(0);

      set(userAction, true);
      applyRouteFilter();
      fetchData().catch(() => {});
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toEqual(0);
    });

    test('check the return types', async () => {
      const { isLoading, state, filters, matchers } =
        useHistoryPaginationFilter<
          EthTransaction,
          TransactionRequestPayload,
          EthTransactionEntry,
          Filters,
          Matcher
        >(
          locationOverview,
          mainPage,
          () => useTransactionFilter(get(protocols).length > 0),
          fetchTransactions,
          {
            onUpdateFilters,
            extraParams,
            customPageParams
          }
        );

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<EthTransactionEntry>>();
      expectTypeOf(get(state).data).toEqualTypeOf<EthTransactionEntry[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    test('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortBy: ['timestamp'], sortDesc: ['false'] };

      const { isLoading, state, pageParams } = useHistoryPaginationFilter<
        EthTransaction,
        TransactionRequestPayload,
        EthTransactionEntry,
        Filters,
        Matcher
      >(
        locationOverview,
        mainPage,
        () => useTransactionFilter(get(protocols).length > 0),
        fetchTransactions,
        {
          onUpdateFilters,
          extraParams,
          customPageParams
        }
      );

      await router.push({
        query
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(route.query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<EthTransactionEntry>>(get(state));
      assertType<EthTransactionEntry[]>(get(state).data);
      assertType<number>(get(state).found);
      expect(get(pageParams).accounts).toHaveLength(1);

      expect(get(state).data).toHaveLength(0);
      expect(get(state).found).toEqual(0);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(0);
    });
  });
});
