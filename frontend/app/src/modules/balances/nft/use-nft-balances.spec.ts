import type { EffectScope, MaybeRef } from 'vue';
import type * as Vue from 'vue';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import type { LocationQuery } from '@/modules/core/table/route';
import { startPromise } from '@shared/utils';
import { updateGeneralSettings } from '@test/utils/general-settings';
import flushPromises from 'flush-promises';
import { err, ok } from 'plainfp/result';
import { afterEach, assertType, beforeEach, describe, expect, expectTypeOf, it, vi } from 'vitest';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { Module } from '@/modules/core/common/modules';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';

vi.mock('vue', async (): Promise<Record<string, unknown>> => {
  const mod = await vi.importActual<typeof Vue>('vue');

  return {
    ...mod,
    onBeforeMount: vi.fn().mockImplementation((fn: () => void): void => fn()),
  };
});

const submitTaskMock = vi.fn();
const notifyErrorMock = vi.fn();

vi.mock('@/modules/task-center/use-native-task', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/task-center/use-native-task')>();
  return {
    ...actual,
    useNativeTask: (): ReturnType<typeof actual.useNativeTask> => ({
      ...actual.useNativeTask(),
      statusOf: () => ({ active: false, everCompleted: false, pending: false, running: false, status: undefined }),
      submitTask: submitTaskMock,
    }),
  };
});

vi.mock('@/modules/core/notifications/use-notifications', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/core/notifications/use-notifications')>();
  return {
    ...actual,
    useNotifications: (): ReturnType<typeof actual.useNotifications> => ({
      ...actual.useNotifications(),
      notifyError: notifyErrorMock,
    }),
  };
});

describe('useNftBalances', () => {
  let fetchNonFungibleBalances: (
    payload: MaybeRef<NonFungibleBalancesRequestPayload>,
  ) => Promise<Collection<NonFungibleBalance>>;
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
    fetchNonFungibleBalances = useNftBalances().fetchNonFungibleBalances;
  });

  afterEach((): void => {
    scope.stop();
    vi.clearAllMocks();
  });

  describe('components::accounts/balances/NonFungibleBalances.vue', () => {
    const ignoredAssetsHandling = ref<string>();
    const extraParams = computed(() => ({
      includeIgnoredTrades: get(ignoredAssetsHandling),
    }));

    const onUpdateFilters = (query: LocationQuery): void => {
      set(ignoredAssetsHandling, query.includeIgnoredTrades);
    };

    beforeEach((): void => {
      set(mainPage, true);
      // Reset shared filter state to the settled baseline (undefined) so each test
      // starts identically. A first mount with an empty route sets this from 'none'
      // to undefined; leaving the 'none' seed leaks across tests.
      set(ignoredAssetsHandling, undefined);
    });

    it('should initialize composable correctly', async () => {
      const {
        filter: filters,
        sort,
        collection: state,
        refetch: fetchData,
        isLoading,
      } = scope.run(() => useServerTable<NonFungibleBalance>({
        fetch: fetchNonFungibleBalances,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        params: [{ fromQuery: onUpdateFilters, to: 'both', values: extraParams }],
        sort: {
          default: [{
            column: 'name',
            direction: 'asc',
          }],
        },
      }))!;

      expect(get(isLoading)).toBe(false);
      expect(get(filters)).to.toStrictEqual({});
      expect(get(sort)).toHaveLength(1);
      expect(get(sort)).toMatchObject([{
        column: 'name',
        direction: 'asc',
      }]);
      expect(get(state).data).toHaveLength(0);
      expect(get(state).total).toBe(0);

      await nextTick();
      startPromise(fetchData());
      expect(get(isLoading)).toBe(true);
      await flushPromises();
      expect(get(state).total).toBe(30);
    });

    it('should return correct types', () => {
      const {
        isLoading,
        collection: state,
        filter: filters,
      } = scope.run(() => useServerTable<NonFungibleBalance>({
        fetch: fetchNonFungibleBalances,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        params: [{ fromQuery: onUpdateFilters, to: 'both', values: extraParams }],
        sort: {
          default: [
            {
              column: 'name',
              direction: 'asc',
            },
          ],
        },
      }))!;

      expect(get(isLoading)).toBe(false);

      expectTypeOf(get(state)).toEqualTypeOf<Collection<NonFungibleBalance>>();
      expectTypeOf(get(state).data).toEqualTypeOf<NonFungibleBalance[]>();
      expectTypeOf(get(state).found).toEqualTypeOf<number>();
      expectTypeOf(get(filters)).toEqualTypeOf<undefined>();
    });

    it('should modify filters and fetch data correctly', async () => {
      const pushSpy = vi.spyOn(router, 'push');
      const query = { sortOrder: ['asc'] };

      const {
        isLoading,
        collection: state,
        sort,
      } = scope.run(() => useServerTable<NonFungibleBalance>({
        fetch: fetchNonFungibleBalances,
        urlState: get(mainPage) ? { mode: 'route' } : { mode: 'none' },
        params: [{ fromQuery: onUpdateFilters, to: 'both', values: extraParams }],
        sort: {
          default: [{
            column: 'name',
            direction: 'desc',
          }],
        },
      }))!;

      expect(get(sort)).toStrictEqual([{
        column: 'name',
        direction: 'desc',
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

      assertType<Collection<NonFungibleBalance>>(get(state));
      assertType<NonFungibleBalance[]>(get(state).data);
      assertType<number>(get(state).found);

      expect(get(state).data).toHaveLength(9);
      expect(get(state).found).toBe(29);
      expect(get(state).total).toBe(30);
      expect(get(sort)).toStrictEqual([{
        column: 'timestamp',
        direction: 'asc',
      }]);
    });
  });

  describe('refreshNonFungibleBalances', () => {
    beforeEach(() => {
      updateGeneralSettings({ activeModules: [Module.NFTS] });
      submitTaskMock.mockReset();
      notifyErrorMock.mockReset();
    });

    it('should notify when the task fails', async () => {
      submitTaskMock.mockResolvedValue(err(TaskFailed({ message: 'boom' })));

      await useNftBalances().refreshNonFungibleBalances(true);

      expect(notifyErrorMock).toHaveBeenCalledOnce();
      expect(notifyErrorMock.mock.calls[0][1]).toContain('boom');
    });

    it('should not notify when the task was cancelled', async () => {
      submitTaskMock.mockResolvedValue(err(Cancelled({ message: 'stopped' })));

      await useNftBalances().refreshNonFungibleBalances(true);

      expect(notifyErrorMock).not.toHaveBeenCalled();
    });

    it('should not notify when the task succeeds', async () => {
      submitTaskMock.mockResolvedValue(ok(undefined));

      await useNftBalances().refreshNonFungibleBalances(true);

      expect(notifyErrorMock).not.toHaveBeenCalled();
    });
  });
});
