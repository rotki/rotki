import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { bigNumberify } from '@rotki/common';
import { createTestExchange } from '@test/utils/create-data';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';

const runTaskMock = vi.fn();
const notifyError = vi.fn();
const queryExchangeBalances = vi.fn();
const callSetupExchange = vi.fn<(payload: ExchangeFormData) => Promise<string>>();

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
    queryRemoveExchange: vi.fn(),
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
    it('should store the balances for the location on success', async () => {
      runTaskMock.mockResolvedValue(ok({ BTC: { amount: '1', value: '50000' } }));

      await exchanges.fetchExchangeBalances({ ignoreCache: false, location: 'kraken' });

      expect(queryExchangeBalances).toHaveBeenCalledWith('kraken', false, undefined);
      const { exchangeBalances } = storeToRefs(store);
      expect(get(exchangeBalances).kraken).toMatchObject({
        BTC: { amount: bigNumberify(1), value: bigNumberify(50000) },
      });
    });

    it('should notify on an actionable failure', async () => {
      runTaskMock.mockResolvedValue(err(TaskFailed({ cause: new Error('boom'), message: 'boom' })));

      await exchanges.fetchExchangeBalances({ ignoreCache: true, location: 'kraken' });

      expect(notifyError).toHaveBeenCalledOnce();
    });

    it('should stay quiet when the task is cancelled', async () => {
      runTaskMock.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      await exchanges.fetchExchangeBalances({ ignoreCache: true, location: 'kraken' });

      expect(notifyError).not.toHaveBeenCalled();
    });
  });
  describe('setupExchange', () => {
    const form: ExchangeFormData = { apiKey: 'key', apiSecret: 'secret', location: 'kraken', mode: 'add', name: 'main', passphrase: '' };

    it('should keep a new connection under the identifier the backend gave it, without its secrets', async () => {
      callSetupExchange.mockResolvedValue('c1');

      expect(await exchanges.setupExchange(form)).toBe(true);

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
});
