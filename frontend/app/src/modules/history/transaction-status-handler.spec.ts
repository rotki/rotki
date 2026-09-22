import { createMock } from '@test/utils/create-mock';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TransactionsQueryStatus, type UnifiedTransactionStatusData } from '@/modules/core/messaging/types';
import { accountSyncActivity, type AccountSyncDetail } from '@/modules/history/events/tx/sync-activity';
import { createTransactionStatusHandler } from '@/modules/history/transaction-status-handler';
import { type ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { readActivityDetail, useActivityDetail } from '@/modules/task-center/use-activity-detail';

const mockReportProgress = vi.fn();
/** The activities the stub orchestrator reports as active, by id. */
const live = new Set<string>();
const changeListeners: (() => void)[] = [];

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn(() => ({
    onChange: (listener: () => void): (() => void) => {
      changeListeners.push(listener);
      return (): void => {};
    },
    reportProgress: mockReportProgress,
    statusOf: (kind: ActivityKind, ...parts: (string | number)[]): { active: boolean } => ({
      active: live.has(makeActivityId(kind, ...parts)),
    }),
  })),
}));

function goLive(chain: string, address: string): void {
  live.add(accountSyncActivity.id({ address, chain }));
}

/** Settles an account's sync as far as the handler can tell, and lets it prune. */
function settle(chain: string, address: string): void {
  live.delete(accountSyncActivity.id({ address, chain }));
  changeListeners.forEach(listener => listener());
}

function evmFrame(status: TransactionsQueryStatus, period: [number, number], address = '0xabc'): UnifiedTransactionStatusData {
  return createMock<UnifiedTransactionStatusData>({
    address,
    chain: 'ETH',
    period,
    status,
    subtype: 'evm',
  });
}

function detailOf(address: string, chain = 'eth'): AccountSyncDetail | undefined {
  return get(readActivityDetail(accountSyncActivity, { address, chain }));
}

describe('createTransactionStatusHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useActivityDetail().resetDetails();
    vi.clearAllMocks();
    live.clear();
    changeListeners.length = 0;
    goLive('eth', '0xabc');
  });

  it('should publish detail under the lowercased chain the activity is keyed by', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [100, 200]));

    const detail = detailOf('0xabc');
    expect(detail?.queryStep).toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED);
    expect(detail?.windowEnd).toBe(200);
  });

  it('should report the started frame as none of the window rather than all of it', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [100, 200]));

    // Taken raw, the overloaded `period[1]` would read 100% before anything was queried.
    expect(mockReportProgress).toHaveBeenCalledWith(
      accountSyncActivity.id({ address: '0xabc', chain: 'eth' }),
      { current: 0, total: 300 },
    );
  });

  it('should report the cursor against the window established by the started frame, over the query\'s three passes', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [100, 200]));
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [100, 150]));

    expect(mockReportProgress).toHaveBeenLastCalledWith(
      accountSyncActivity.id({ address: '0xabc', chain: 'eth' }),
      { current: 50, total: 300 },
    );
  });

  it('should fan a batched bitcoin frame out into one publish per address', async () => {
    goLive('btc', 'bc1a');
    goLive('btc', 'bc1b');
    const handler = createTransactionStatusHandler();

    await handler.handle(createMock<UnifiedTransactionStatusData>({
      addresses: ['bc1a', 'bc1b'],
      chain: 'BTC',
      period: undefined,
      status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
      subtype: 'bitcoin',
    }));

    for (const address of ['bc1a', 'bc1b'])
      expect(detailOf(address, 'btc')?.queryStep).toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS);
  });

  it('should leave a period-less chain indeterminate rather than reporting a made-up total', async () => {
    goLive('btc', 'bc1a');
    const handler = createTransactionStatusHandler();

    await handler.handle(createMock<UnifiedTransactionStatusData>({
      addresses: ['bc1a'],
      chain: 'BTC',
      period: undefined,
      status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
      subtype: 'bitcoin',
    }));

    expect(mockReportProgress).not.toHaveBeenCalled();
  });

  it('should publish nothing for a frame about an account whose sync is not running', async () => {
    const handler = createTransactionStatusHandler();

    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [100, 150], '0xlate'));

    expect(detailOf('0xlate')).toBeUndefined();
    expect(mockReportProgress).not.toHaveBeenCalled();
  });

  it('should keep a cancelled account at the detail it had reached when a late frame arrives', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [100, 150]));

    settle('eth', '0xabc');
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, [100, 200]));

    expect(detailOf('0xabc')?.queryStep).toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS);
    expect(detailOf('0xabc')?.period).toEqual([100, 150]);
  });

  it('should measure a new run against its own window, not the one the last run established', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 150]));

    settle('eth', '0xabc');
    goLive('eth', '0xabc');
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [0, 400]));
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 300]));

    // The last run's first cursor, 150, would otherwise stay the start of the window.
    expect(mockReportProgress).toHaveBeenLastCalledWith(
      accountSyncActivity.id({ address: '0xabc', chain: 'eth' }),
      { current: 0, total: 300 },
    );
  });

  it('should ignore an account-change frame, which carries no query progress', async () => {
    const handler = createTransactionStatusHandler();

    await handler.handle(evmFrame(TransactionsQueryStatus.ACCOUNT_CHANGE, [0, 150]));

    expect(detailOf('0xabc')).toBeUndefined();
  });
});
