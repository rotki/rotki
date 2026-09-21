import { describe, expect, it } from 'vitest';
import { TransactionsQueryStatus, type UnifiedTransactionStatusData } from '@/modules/core/messaging/types';
import { mergeTxFrame, periodSteps, type TxAccountTracking } from '@/modules/history/tx-query-status-period';

const NOW = 5000;

function evm(status: TransactionsQueryStatus, period: [number, number]): UnifiedTransactionStatusData {
  return { address: '0x123', chain: 'eth', period, status, subtype: 'evm' };
}

function bitcoin(status: TransactionsQueryStatus, period?: [number, number]): UnifiedTransactionStatusData {
  return { addresses: ['bc1abc'], chain: 'btc', period, status, subtype: 'bitcoin' };
}

/** Folds a run's frames into one account's tracking, as the handler does. */
function fold(...frames: UnifiedTransactionStatusData[]): TxAccountTracking | undefined {
  return frames.reduce<TxAccountTracking | undefined>((tracking, frame) => mergeTxFrame(frame, tracking, NOW), undefined);
}

describe('mergeTxFrame', () => {
  it('should park the cursor at the start of the range on STARTED, where raw it would read as 100%, keeping the target end', () => {
    expect(fold(evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [100, 1000]))).toMatchObject({
      originalPeriodEnd: 1000,
      period: [100, 100],
    });
  });

  it('should advance the cursor across the message sequence, which the STARTED normalisation must not stall', () => {
    const started = fold(evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [0, 1000]));
    expect(started?.period).toEqual([0, 0]);

    const querying = mergeTxFrame(evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 400]), started, NOW);
    expect(querying.period).toEqual([0, 400]);

    expect(mergeTxFrame(evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED, [0, 1000]), querying, NOW)).toMatchObject({
      originalPeriodEnd: 1000,
      period: [0, 1000],
    });
  });

  it('should keep the target end STARTED established on later frames', () => {
    expect(fold(
      evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [0, 2000]),
      evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 1500]),
    )).toMatchObject({ originalPeriodEnd: 2000, period: [0, 1500] });
  });

  it('should take no window start from STARTED, whose period[1] is the end', () => {
    expect(fold(evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [0, 2000]))?.originalPeriodStart).toBeUndefined();
  });

  it('should take the window start from the first cursor after STARTED, and keep it', () => {
    expect(fold(
      evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [0, 2000]),
      evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 1800]),
      evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 1500]),
    )).toMatchObject({ originalPeriodEnd: 2000, originalPeriodStart: 1800, period: [0, 1500] });
  });

  it('should use a non-zero period[0] as the window start', () => {
    expect(fold(evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [500, 2000]))?.originalPeriodStart).toBe(500);
  });

  it('should measure a run whose STARTED frame was missed against the moment the account was first seen', () => {
    expect(fold(evm(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 1800]))?.originalPeriodEnd).toBe(NOW);
  });

  it('should track a bitcoin period the same way as every other subtype', () => {
    expect(fold(
      bitcoin(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [0, 1000]),
      bitcoin(TransactionsQueryStatus.QUERYING_TRANSACTIONS, [0, 600]),
    )).toMatchObject({ originalPeriodEnd: 1000, originalPeriodStart: 600, period: [0, 600] });
  });

  it('should keep a bitcoin period when a later frame omits it', () => {
    expect(fold(
      bitcoin(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED, [0, 1000]),
      bitcoin(TransactionsQueryStatus.QUERYING_TRANSACTIONS),
    )).toMatchObject({
      originalPeriodEnd: 1000,
      period: [0, 0],
      status: TransactionsQueryStatus.QUERYING_TRANSACTIONS,
    });
  });

  it('should leave bitcoin without a window when its frames carry no period, rather than invent one', () => {
    const tracking = fold(bitcoin(TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED));

    expect(tracking?.period).toBeUndefined();
    expect(tracking?.originalPeriodEnd).toBeUndefined();
  });
});

describe('periodSteps', () => {
  it('should measure the cursor against the established window', () => {
    expect(periodSteps({ originalPeriodEnd: 200, originalPeriodStart: 100, period: [100, 150] }))
      .toStrictEqual({ current: 50, total: 100 });
  });

  it('should fall back to the period start when no original start was captured', () => {
    expect(periodSteps({ originalPeriodEnd: 200, period: [100, 125] }))
      .toStrictEqual({ current: 25, total: 100 });
  });

  it('should report nothing for a query that sends no period', () => {
    expect(periodSteps({ originalPeriodEnd: 200 })).toBeUndefined();
  });

  it('should report nothing before the target has been established', () => {
    expect(periodSteps({ period: [100, 150] })).toBeUndefined();
  });

  it('should report nothing for an empty window rather than claiming a percentage', () => {
    expect(periodSteps({ originalPeriodEnd: 100, originalPeriodStart: 100, period: [100, 100] }))
      .toBeUndefined();
  });

  it('should report nothing for a window that ends before it starts', () => {
    expect(periodSteps({ originalPeriodEnd: 50, originalPeriodStart: 100, period: [100, 100] }))
      .toBeUndefined();
  });

  it('should clamp a cursor that has run past the window', () => {
    expect(periodSteps({ originalPeriodEnd: 200, originalPeriodStart: 100, period: [100, 999] }))
      .toStrictEqual({ current: 100, total: 100 });
  });

  it('should clamp a cursor that sits before the window', () => {
    expect(periodSteps({ originalPeriodEnd: 200, originalPeriodStart: 100, period: [100, 40] }))
      .toStrictEqual({ current: 0, total: 100 });
  });
});
