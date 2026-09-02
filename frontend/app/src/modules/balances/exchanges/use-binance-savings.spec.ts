import type { AssetBalance } from '@rotki/common';
import type { EffectScope, MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { ExchangeSavingsCollection, ExchangeSavingsEvent, ExchangeSavingsRequestPayload } from '@/modules/balances/types/exchanges';
import type { Collection } from '@/modules/core/common/collection';
import { startPromise } from '@shared/utils';
import flushPromises from 'flush-promises';
import { err, ok } from 'plainfp/result';
import { afterEach, assertType, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useBinanceSavings } from '@/modules/balances/exchanges/use-binance-savings';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';

const mocks = vi.hoisted(() => ({
  submitTask: vi.fn(),
  workStatus: { active: false, everCompleted: false, pending: false, running: false },
}));

const notifyError = vi.fn();

vi.mock('vue', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void): void => fn()),
  };
});

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    reportProgress: vi.fn(),
    runTaskResult: vi.fn(),
    submitTask: mocks.submitTask,
  })),
}));

vi.mock('@/modules/task-center/use-task-center', async () => {
  const vue = await import('vue');
  return {
    useTaskCenter: vi.fn(() => ({
      useWorkStatus: (): unknown => vue.computed(() => mocks.workStatus),
    })),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNotifications: vi.fn(() => ({ notifyError, showErrorMessage: vi.fn() })),
}));

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

  describe('refreshExchangeSavings', () => {
    beforeEach((): void => {
      setActivePinia(createPinia());
      mocks.submitTask.mockResolvedValue(ok(undefined));
      mocks.workStatus.active = false;
      mocks.workStatus.everCompleted = false;
      useConnectedExchangesStore().setConnectedExchanges([
        { location: 'binance', name: 'binance' },
        { location: 'binanceus', name: 'binanceus' },
        { location: 'kraken', name: 'kraken' },
      ]);
    });

    it('should submit one native activity per binance location', async () => {
      await useBinanceSavings().refreshExchangeSavings(true);

      expect(mocks.submitTask).toHaveBeenCalledTimes(2);
      const ids = mocks.submitTask.mock.calls.map(([spec]) => spec.id);
      expect(ids).toStrictEqual([
        makeActivityId(ActivityKind.EXCHANGE_SAVINGS, 'binance'),
        makeActivityId(ActivityKind.EXCHANGE_SAVINGS, 'binanceus'),
      ]);
      expect(mocks.submitTask.mock.calls[0][0]).toMatchObject({
        kind: ActivityKind.EXCHANGE_SAVINGS,
        rerunnable: true,
      });
    });

    it('should skip an automatic refresh once savings have loaded', async () => {
      mocks.workStatus.everCompleted = true;

      await useBinanceSavings().refreshExchangeSavings(false);

      expect(mocks.submitTask).not.toHaveBeenCalled();
    });

    it('should skip while a sync is already in flight', async () => {
      mocks.workStatus.active = true;

      await useBinanceSavings().refreshExchangeSavings(true);

      expect(mocks.submitTask).not.toHaveBeenCalled();
    });

    it('should notify on an actionable failure', async () => {
      mocks.submitTask.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      await useBinanceSavings().refreshExchangeSavings(true);

      expect(notifyError).toHaveBeenCalledTimes(2);
    });
  });
});
