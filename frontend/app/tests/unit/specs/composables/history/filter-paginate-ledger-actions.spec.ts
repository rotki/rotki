import flushPromises from 'flush-promises';
import type { Filters, Matcher } from '@/composables/filters/ledger-actions';
import type { Collection } from '@/types/collection';
import type {
  LedgerAction,
  LedgerActionEntry,
  LedgerActionRequestPayload
} from '@/types/history/ledger-action/ledger-actions';
import type { MaybeRef } from '@vueuse/core';
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
  let fetchLedgerActions: (
    payload: MaybeRef<LedgerActionRequestPayload>
  ) => Promise<Collection<LedgerActionEntry>>;
  const locationOverview: MaybeRef<string | null> = ref('');
  const mainPage: Ref<boolean> = ref(false);
  const router = useRouter();
  const route = useRoute();

  beforeAll(() => {
    setActivePinia(createPinia());
    fetchLedgerActions = useLedgerActions().fetchLedgerActions;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('components::history/trades/LedgerActionContent', () => {
    set(locationOverview, '');

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
      } = usePaginationFilters<
        LedgerAction,
        LedgerActionRequestPayload,
        LedgerActionEntry,
        Collection<LedgerActionEntry>,
        Filters,
        Matcher
      >(locationOverview, mainPage, useLedgerActionsFilter, fetchLedgerActions);

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
      expect(get(state).total).toEqual(3);
    });

    test('check the return types', async () => {
      const { isLoading, state, filters, matchers } = usePaginationFilters<
        LedgerAction,
        LedgerActionRequestPayload,
        LedgerActionEntry,
        Collection<LedgerActionEntry>,
        Filters,
        Matcher
      >(locationOverview, mainPage, useLedgerActionsFilter, fetchLedgerActions);

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<LedgerActionEntry>>();
      expectTypeOf(get(state).data).toEqualTypeOf<LedgerActionEntry[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<Filters>();
      expectTypeOf(get(matchers)).toEqualTypeOf<Matcher[]>();
    });

    test('modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortBy: ['location'], sortDesc: ['true'] };

      const { isLoading, state } = usePaginationFilters<
        LedgerAction,
        LedgerActionRequestPayload,
        LedgerActionEntry,
        Collection<LedgerActionEntry>,
        Filters,
        Matcher
      >(locationOverview, mainPage, useLedgerActionsFilter, fetchLedgerActions);

      await router.push({
        query
      });

      expect(pushSpy).toHaveBeenCalledOnce();
      expect(pushSpy).toHaveBeenCalledWith({ query });
      expect(route.query).toEqual(query);
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(isLoading)).toBe(false);

      assertType<Collection<LedgerActionEntry>>(get(state));
      assertType<LedgerActionEntry[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(3);
      expect(get(state).found).toEqual(3);
      expect(get(state).limit).toEqual(-1);
      expect(get(state).total).toEqual(3);
    });
  });
});
