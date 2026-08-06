import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';

const runTaskMock = vi.fn();
const processHistoricalBalancesMock = vi.fn(async () => ({ taskId: 1 }));

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

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: vi.fn(() => ({
    processHistoricalBalances: processHistoricalBalancesMock,
  })),
}));

describe('useHistoricalBalances', () => {
  let trigger: ReturnType<typeof useHistoricalBalances>['triggerHistoricalBalancesProcessing'];

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', 'true');
    ({ triggerHistoricalBalancesProcessing: trigger } = useHistoricalBalances());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('should process historical balances through the orchestrator', async () => {
    runTaskMock.mockResolvedValue(ok(true));

    await trigger();

    expect(processHistoricalBalancesMock).toHaveBeenCalledOnce();
  });

  it('should do nothing when the accounting update flag is off', async () => {
    vi.stubEnv('VITE_ACCOUNTING_UPDATE', '');
    runTaskMock.mockResolvedValue(ok(true));

    await trigger();

    expect(processHistoricalBalancesMock).not.toHaveBeenCalled();
  });

  it('should rethrow an actionable processing failure', async () => {
    runTaskMock.mockResolvedValue(err(TaskFailed({ cause: new Error('boom'), message: 'boom' })));

    await expect(trigger()).rejects.toThrow('boom');
  });

  it('should stay quiet when the task is cancelled', async () => {
    runTaskMock.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

    await expect(trigger()).resolves.toBeUndefined();
  });
});
