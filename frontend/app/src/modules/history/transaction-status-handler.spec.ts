import { createMock } from '@test/utils/create-mock';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TransactionsQueryStatus, type UnifiedTransactionStatusData } from '@/modules/core/messaging/types';
import { accountSyncActivity } from '@/modules/history/events/tx/sync-activity';
import { createTransactionStatusHandler } from '@/modules/history/transaction-status-handler';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { readActivityDetail, useActivityDetail } from '@/modules/task-center/use-activity-detail';

const mockReportProgress = vi.fn();

vi.mock('@/modules/task-center/use-task-orchestrator', () => ({
  useTaskOrchestrator: vi.fn(() => ({
    reportProgress: mockReportProgress,
  })),
}));

function evmFrame(status: TransactionsQueryStatus, period: [number, number]): UnifiedTransactionStatusData {
  return createMock<UnifiedTransactionStatusData>({
    address: '0xabc',
    chain: 'ETH',
    period,
    status,
    subtype: 'evm',
  });
}

describe('createTransactionStatusHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useActivityDetail().resetDetails();
    vi.clearAllMocks();
    useTxQueryStatusStore().initializeQueryStatus([{ address: '0xabc', chain: 'eth', subtype: 'evm' }]);
  });

  it('should publish detail under the lowercased chain the activity is keyed by', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [100, 200]));

    const detail = get(readActivityDetail(accountSyncActivity, { address: '0xabc', chain: 'eth' }));
    expect(detail?.queryStep).toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED);
    expect(detail?.windowEnd).toBe(200);
  });

  it('should report the started frame as none of the window rather than all of it', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [100, 200]));

    // Taken raw, the overloaded `period[1]` would read 100% before anything was queried.
    expect(mockReportProgress).toHaveBeenCalledWith(
      accountSyncActivity.id({ address: '0xabc', chain: 'eth' }),
      { current: 0, total: 100 },
    );
  });

  it('should report the cursor against the window established by the started frame', async () => {
    const handler = createTransactionStatusHandler();
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [100, 200]));
    await handler.handle(evmFrame(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [100, 150]));

    expect(mockReportProgress).toHaveBeenCalledWith(
      accountSyncActivity.id({ address: '0xabc', chain: 'eth' }),
      { current: 50, total: 100 },
    );
  });

  it('should fan a batched bitcoin frame out into one publish per address', async () => {
    useTxQueryStatusStore().initializeQueryStatus([
      { address: 'bc1a', chain: 'btc', subtype: 'bitcoin' },
      { address: 'bc1b', chain: 'btc', subtype: 'bitcoin' },
    ]);
    const handler = createTransactionStatusHandler();

    await handler.handle(createMock<UnifiedTransactionStatusData>({
      addresses: ['bc1a', 'bc1b'],
      chain: 'BTC',
      period: undefined,
      status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
      subtype: 'bitcoin',
    }));

    for (const address of ['bc1a', 'bc1b']) {
      expect(get(readActivityDetail(accountSyncActivity, { address, chain: 'btc' }))?.queryStep)
        .toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS);
    }
  });

  it('should leave a period-less chain indeterminate rather than reporting a made-up total', async () => {
    useTxQueryStatusStore().initializeQueryStatus([{ address: 'bc1a', chain: 'btc', subtype: 'bitcoin' }]);
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

  it('should publish nothing for a frame that lands after the sync has ended', async () => {
    const store = useTxQueryStatusStore();
    store.stopSyncing();
    const handler = createTransactionStatusHandler();

    await handler.handle(createMock<UnifiedTransactionStatusData>({
      address: '0xlate',
      chain: 'ETH',
      period: [100, 150],
      status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
      subtype: 'evm',
    }));

    expect(get(readActivityDetail(accountSyncActivity, { address: '0xlate', chain: 'eth' })))
      .toBeUndefined();
    expect(mockReportProgress).not.toHaveBeenCalled();
  });
});
