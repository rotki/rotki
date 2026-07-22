import type { AssetBalance } from '@rotki/common';
import type { EffectScope, MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { ExchangeSavingsCollection, ExchangeSavingsEvent, ExchangeSavingsRequestPayload } from '@/modules/balances/types/exchanges';
import type { Collection } from '@/modules/core/common/collection';
import { startPromise } from '@shared/utils';
import flushPromises from 'flush-promises';
import { afterEach, assertType, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useBinanceSavings } from '@/modules/balances/exchanges/use-binance-savings';
import { useServerTable } from '@/modules/core/table/use-server-table';

vi.mock('vue', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void): void => fn()),
  };
});

describe('useBinanceSavings', () => {
  let fetchExchangeSavings: (payload: MaybeRef<ExchangeSavingsRequestPayload>) => Promise<ExchangeSavingsCollection>;
  const exchange = ref<string>('binance');
  const mainPage = ref<boolean>(false);
  const router = useRouter();
  const route = useRoute();
  let scope: EffectScope;

  beforeEach(async (): Promise<void> => {
    scope = effectScope();
    setActivePinia(createPinia());
    // Reset the shared route query (mutated by other tests' router.push). A fresh
    // useRouter() call returns its own push mock, so this does not affect the
    // push spy asserted on the describe-level router instance.
    await useRouter().push({ query: {} });
    fetchExchangeSavings = useBinanceSavings().fetchExchangeSavings;
  });

  afterEach((): void => {
    scope.stop();
    vi.clearAllMocks();
  });

  describe('components::exchanges/BinanceSavingDetail.vue', () => {
    const exchangeReceived = ref<AssetBalance[]>([]);
    const exchangeAssets = ref<string[]>([]);
    const defaultParams = computed(() => ({
      location: get(exchange).toString(),
    }));

    async function fetchSavings(payload: MaybeRef<ExchangeSavingsRequestPayload>): Promise<Collection<ExchangeSavingsEvent>> {
      const { received = [], assets = [], ...collection } = await fetchExchangeSavings(payload);
      set(exchangeAssets, assets);
      set(exchangeReceived, received);
      return collection;
    }

    beforeEach((): void => {
      set(mainPage, true);
      set(exchangeAssets, []);
      set(exchangeReceived, []);
    });

    it('should initialize composable correctly', async () => {
      const { filter: filters, sort, collection: state, refetch: fetchData, isLoading } = scope.run(() => useServerTable<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload
      >({
        fetch: fetchSavings,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        params: [{ isDefault: true, to: 'request', values: defaultParams }],
        sort: {
          default: [{
            direction: 'asc',
          }],
        },
      }))!;

      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(sort)).toHaveLength(1);
      expect(get(sort)).toMatchObject([
        {
          column: 'timestamp',
          direction: 'asc',
        },
      ]);
      expect(get(state).data).toHaveLength(0);
      expect(get(exchangeAssets)).toHaveLength(0);
      expect(get(exchangeReceived)).toHaveLength(0);
      expect(get(state).total).toBe(0);

      await nextTick();
      startPromise(fetchData());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      await flushPromises();
      expect(get(isLoading)).toBe(false);
      expect(get(state).total).toBe(260);
    });

    it('should return correct types', () => {
      const { isLoading, collection: state, filter: filters } = scope.run(() => useServerTable<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload
      >({
        fetch: fetchExchangeSavings,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        params: [{ isDefault: true, to: 'request', values: defaultParams }],
        sort: {
          default: [{
            direction: 'asc',
          }],
        },
      }))!;

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<ExchangeSavingsEvent>>();
      expectTypeOf(get(state).data).toEqualTypeOf<ExchangeSavingsEvent[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<undefined>();
    });

    it('should modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortOrder: ['desc'] };

      const { isLoading, collection: state, sort } = scope.run(() => useServerTable<
        ExchangeSavingsEvent,
        ExchangeSavingsRequestPayload
      >({
        fetch: fetchSavings,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        params: [{ isDefault: true, to: 'request', values: defaultParams }],
        sort: {
          default: [{
            direction: 'asc',
          }],
        },
      }))!;

      expect(get(sort)).toStrictEqual([{
        column: 'timestamp',
        direction: 'asc',
      }]);

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

      assertType<Collection<ExchangeSavingsEvent>>(get(state));
      assertType<ExchangeSavingsEvent[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(10);
      expect(get(exchangeAssets)).toHaveLength(2);
      expect(get(exchangeReceived)).toHaveLength(2);
      expect(get(state).found).toBe(260);
      expect(get(state).total).toBe(260);
      expect(get(sort)).toStrictEqual([{
        column: 'timestamp',
        direction: 'desc',
      }]);
    });
  });
});
