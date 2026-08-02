import { bigNumberify } from '@rotki/common';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';

const runTaskMock = vi.fn();
const notifyError = vi.fn();
const queryExchangeBalances = vi.fn();

// Native producer path: real useNativeTask + orchestrator drive submitTask; only the task handler
// the facade delegates to is mocked, so runTask resolves from runTaskMock.
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
    callSetupExchange: vi.fn(),
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
    // The api call returns a pending task; the activity records its id so a cancel can abort it.
    queryExchangeBalances.mockResolvedValue({ taskId: 1 });
  });

  describe('fetchExchangeBalances', () => {
    it('should store the balances for the location on success', async () => {
      // Backend Balance.serialize() emits { amount, value } (post usd_value -> value migration).
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
});
