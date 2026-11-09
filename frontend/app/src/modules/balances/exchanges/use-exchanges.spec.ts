import type { Exchange, ExchangeFormData } from '@/modules/balances/types/exchanges';
import { bigNumberify } from '@rotki/common';
import { createTestExchange } from '@test/utils/create-data';
import { flushPromises } from '@vue/test-utils';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { exchangeBalancesActivity } from '@/modules/balances/balances.activity';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityStatus } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

const runTaskMock = vi.fn();
const notifyError = vi.fn();
const queryExchangeBalances = vi.fn();
const callSetupExchange = vi.fn<(payload: ExchangeFormData) => Promise<string>>();
const queryRemoveExchange = vi.fn<(exchange: Exchange) => Promise<boolean>>();

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useTaskHandler: vi.fn(() => ({
      runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
        await taskFn();
        return runTaskMock(taskFn, ...rest);
      },
    })),
  };
});

vi.mock('@/modules/balances/api/use-exchange-api', () => ({
  useExchangeApi: vi.fn(() => ({
    callSetupExchange,
    queryExchangeBalances,
    queryRemoveExchange,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useNotifications: vi.fn(() => ({ notifyError, showErrorMessage: vi.fn() })),
}));

vi.mock('@/modules/assets/amount-display/use-usd-value-threshold', () => ({
  useValueThreshold: vi.fn(() => undefined),
}));

describe('useExchanges', () => {
  let store: ReturnType<typeof useBalancesStore>;
  let exchanges: ReturnType<typeof useExchanges>;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useBalancesStore();
    exchanges = useExchanges();
    vi.clearAllMocks();
    queryExchangeBalances.mockResolvedValue({ taskId: 1 });
  });

  describe('fetchExchangeBalances', () => {
    it('should store each connection separately while keeping location totals', async () => {
      store.exchangeAccountBalances = { binance: {}, kraken: { stale: {} } };
      runTaskMock.mockResolvedValue(ok({
        perAccount: {
          kraken: {
            'key-main': { BTC: { amount: '1', value: '50000' } },
            'key-trading': { BTC: { amount: '2', value: '100000' } },
          },
        },
        totals: { kraken: { BTC: { amount: '3', value: '150000' } } },
      }));

      await exchanges.fetchExchangeBalances({ ignoreCache: false, location: 'kraken' });

      expect(queryExchangeBalances).toHaveBeenCalledWith('kraken', false, undefined);
      const { exchangeBalances } = storeToRefs(store);
      expect(get(exchangeBalances).kraken).toMatchObject({
        BTC: { amount: bigNumberify(3), value: bigNumberify(150000) },
      });
      expect(store.exchangeAccountBalances).toEqual({
        binance: {},
        kraken: {
          'key-main': { BTC: { amount: bigNumberify(1), value: bigNumberify(50000) } },
          'key-trading': { BTC: { amount: bigNumberify(2), value: bigNumberify(100000) } },
        },
      });
    });

    it('should bypass the backend cache on a rerun, which would replay a cached failure', async () => {
      runTaskMock.mockResolvedValue(err(TaskFailed({ message: 'API request failed' })));
      await exchanges.fetchExchangeBalances({ ignoreCache: false, location: 'kraken' });
      await flushPromises();
      expect(queryExchangeBalances).toHaveBeenLastCalledWith('kraken', false, undefined);

      useTaskOrchestrator().rerun(exchangeBalancesActivity.id({ location: 'kraken' }));
      await flushPromises();

      expect(queryExchangeBalances).toHaveBeenCalledTimes(2);
      expect(queryExchangeBalances).toHaveBeenLastCalledWith('kraken', true, undefined);
    });

    it('should update healthy connections and retain failed accounts and totals on partial failure', async () => {
      const { exchangeBalances } = storeToRefs(store);
      set(exchangeBalances, { kraken: { BTC: { amount: bigNumberify(2), value: bigNumberify(100000) } } });
      store.exchangeAccountBalances = { kraken: { 'kraken-main': { BTC: { amount: bigNumberify(2), value: bigNumberify(100000) } } } };
      runTaskMock.mockResolvedValue(ok({
        failedAccounts: { kraken: { 'kraken-main': { cause: 'network', message: 'API request failed' } } },
        perAccount: { kraken: { other: { BTC: { amount: '1', value: '50000' } } } },
        totals: { kraken: { BTC: { amount: '1', value: '50000' } } },
      }));

      await exchanges.fetchExchangeBalances({ ignoreCache: true, location: 'kraken' });

      expect(get(exchangeBalances).kraken).toMatchObject({ BTC: { amount: bigNumberify(2) } });
      expect(store.exchangeAccountBalances.kraken).toEqual({
        'kraken-main': { BTC: { amount: bigNumberify(2), value: bigNumberify(100000) } },
        'other': { BTC: { amount: bigNumberify(1), value: bigNumberify(50000) } },
      });
    });

    it('should store healthy connection balances on a fresh login despite another connection failing', async () => {
      runTaskMock.mockResolvedValue(ok({
        failedAccounts: { kraken: { expired: { cause: 'auth', message: 'Invalid key' } } },
        perAccount: { kraken: { healthy: { BTC: { amount: '1', value: '50000' } } } },
        totals: { kraken: { BTC: { amount: '1', value: '50000' } } },
      }));

      await exchanges.fetchExchangeBalances({ location: 'kraken' });

      expect(store.exchangeAccountBalances.kraken).toEqual({
        healthy: { BTC: { amount: bigNumberify(1), value: bigNumberify(50000) } },
      });
      expect(store.exchangeBalances).toEqual({});
    });

    it.each([
      ['a rejected key alone offers no retry', [['one', 'auth']], 'auth'],
      ['connections that all need fixing report the first cause', [['one', 'auth'], ['two', 'forbidden']], 'auth'],
      ['any connection that could heal offers a retry', [['one', 'auth'], ['two', 'network']], 'network'],
    ])('should report the cause of the failed connections: %s', async (_title, failed, expected) => {
      runTaskMock.mockResolvedValue(ok({
        failedAccounts: { kraken: Object.fromEntries(failed.map(([identifier, cause]) => [identifier, { cause, message: 'failed' }])) },
        perAccount: {},
        totals: {},
      }));

      await exchanges.fetchExchangeBalances({ location: 'kraken' });
      await flushPromises();

      const activity = get(useTaskOrchestrator().activities).find(({ id }) => id === exchangeBalancesActivity.id({ location: 'kraken' }));
      expect(activity?.failureCause).toBe(expected);
    });

    it('should fail the task with the connection errors when a connection of the location failed', async () => {
      useConnectedExchangesStore().setConnectedExchanges([
        createTestExchange('kraken', 'a'),
        createTestExchange('kraken', 'b'),
      ]);
      runTaskMock.mockResolvedValue(ok({
        failedAccounts: { kraken: { 'kraken-a': { cause: 'network', message: 'first failed' }, 'kraken-b': { cause: 'auth', message: 'second failed' } } },
        perAccount: {},
        totals: {},
      }));

      await exchanges.fetchExchangeBalances({ ignoreCache: true, location: 'kraken' });
      await flushPromises();

      const activity = get(useTaskOrchestrator().activities).find(({ id }) => id === exchangeBalancesActivity.id({ location: 'kraken' }));
      expect(activity?.status).toBe(ActivityStatus.FAILED);
      expect(activity?.reason).toContain('a: first failed b: second failed');
    });

    it('should store the balances when only another location failed', async () => {
      runTaskMock.mockResolvedValue(ok({
        failedAccounts: { binance: { 'binance-main': { cause: 'network', message: 'API request failed' } } },
        perAccount: {},
        totals: { kraken: { BTC: { amount: '1', value: '50000' } } },
      }));

      await exchanges.fetchExchangeBalances({ ignoreCache: true, location: 'kraken' });

      expect(get(storeToRefs(store).exchangeBalances).kraken).toMatchObject({ BTC: { amount: bigNumberify(1) } });
    });

    it('should leave an actionable failure to its dock row', async () => {
      runTaskMock.mockResolvedValue(err(TaskFailed({ cause: new Error('boom'), message: 'boom' })));

      await exchanges.fetchExchangeBalances({ ignoreCache: true, location: 'kraken' });

      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should stay quiet when the task is cancelled', async () => {
      runTaskMock.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      await exchanges.fetchExchangeBalances({ ignoreCache: true, location: 'kraken' });

      expect(notifyError).not.toHaveBeenCalled();
    });
  });

  describe('removeExchange balance cleanup', () => {
    it('should remove only the deleted connection balance if the remaining query fails', async () => {
      const main = createTestExchange('kraken', 'main');
      const other = createTestExchange('kraken', 'other');
      useConnectedExchangesStore().setConnectedExchanges([main, other]);
      store.exchangeAccountBalances = {
        kraken: {
          [main.identifier]: { BTC: { amount: bigNumberify(1), value: bigNumberify(50000) } },
          [other.identifier]: { BTC: { amount: bigNumberify(2), value: bigNumberify(100000) } },
        },
        binance: {},
      };
      store.exchangeBalances = { kraken: { BTC: { amount: bigNumberify(3), value: bigNumberify(150000) } } };
      queryRemoveExchange.mockResolvedValue(true);
      runTaskMock.mockResolvedValue(err(TaskFailed({ message: 'offline' })));

      expect(await exchanges.removeExchange(main)).toBe(true);

      expect(store.exchangeAccountBalances).toEqual({
        kraken: { [other.identifier]: { BTC: { amount: bigNumberify(2), value: bigNumberify(100000) } } },
        binance: {},
      });
      expect(store.exchangeBalances).toEqual({
        kraken: { BTC: { amount: bigNumberify(2), value: bigNumberify(100000) } },
      });
      expect(useConnectedExchangesStore().connectedExchanges).toEqual([other]);
    });

    it('should clear the location after its last connection is removed', async () => {
      const main = createTestExchange('kraken', 'main');
      useConnectedExchangesStore().setConnectedExchanges([main]);
      store.exchangeAccountBalances = { kraken: { [main.identifier]: {} }, binance: {} };
      store.exchangeBalances = { kraken: { BTC: { amount: bigNumberify(1), value: bigNumberify(50000) } } };
      queryRemoveExchange.mockResolvedValue(true);

      expect(await exchanges.removeExchange(main)).toBe(true);

      expect(store.exchangeAccountBalances).toEqual({ binance: {} });
      expect(store.exchangeBalances).toEqual({});
    });
  });
  describe('setupExchange', () => {
    const form: ExchangeFormData = { apiKey: 'key', apiSecret: 'secret', location: 'kraken', mode: 'add', name: 'main', passphrase: '' };

    it('should keep a new connection under the identifier the backend gave it, without its secrets', async () => {
      callSetupExchange.mockResolvedValue('c1');

      await exchanges.setupExchange(form);

      expect(get(storeToRefs(useConnectedExchangesStore()).connectedExchanges)).toEqual([
        { connector: 'kraken', identifier: 'c1', location: 'kraken', name: 'main' },
      ]);
    });

    it('should rename an edited connection found by its identifier', async () => {
      const kraken = createTestExchange('kraken', 'main');
      useConnectedExchangesStore().setConnectedExchanges([createTestExchange('kraken', 'other'), kraken]);
      callSetupExchange.mockResolvedValue(kraken.identifier);

      await exchanges.setupExchange({ ...form, identifier: kraken.identifier, mode: 'edit', newName: 'renamed' });

      expect(get(storeToRefs(useConnectedExchangesStore()).connectedExchanges).map(({ identifier, name }) => [identifier, name])).toEqual([
        ['kraken-other', 'other'],
        [kraken.identifier, 'renamed'],
      ]);
    });
  });

  describe('removeExchange', () => {
    const kraken = createTestExchange('kraken', 'main');

    beforeEach(() => {
      useConnectedExchangesStore().setConnectedExchanges([kraken]);
    });

    it('should drop the exchange from the connected list once the backend removed it', async () => {
      queryRemoveExchange.mockResolvedValue(true);

      await expect(exchanges.removeExchange(kraken)).resolves.toBe(true);

      expect(get(storeToRefs(useConnectedExchangesStore()).connectedExchanges)).toEqual([]);
    });

    it('should reject with the error, for the page to name, when the removal fails', async () => {
      const error = new Error('exchange is busy');
      queryRemoveExchange.mockRejectedValue(error);

      await expect(exchanges.removeExchange(kraken)).rejects.toBe(error);

      expect(get(storeToRefs(useConnectedExchangesStore()).connectedExchanges)).toEqual([kraken]);
    });

    it('should resolve false, quietly, when the request was cancelled', async () => {
      queryRemoveExchange.mockRejectedValue(new RequestCancelledError());

      await expect(exchanges.removeExchange(kraken)).resolves.toBe(false);
    });
  });
});
