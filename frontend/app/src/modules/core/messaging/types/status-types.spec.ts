import { describe, expect, it } from 'vitest';
import { TransactionsQueryStatus, UnifiedTransactionStatusData } from './status-types';

describe('unifiedTransactionStatusData', () => {
  const payload = {
    address: '0x123',
    chain: 'base',
    period: [0, 1000],
    subtype: 'evm',
  };

  it('should fold the backend querying_transactions_failed into FAILED, the only failure the frontend knows', () => {
    expect(UnifiedTransactionStatusData.parse({ ...payload, status: 'querying_transactions_failed' }).status)
      .toBe(TransactionsQueryStatus.FAILED);
  });

  it('should keep every other status as sent', () => {
    expect(UnifiedTransactionStatusData.parse({ ...payload, status: 'querying_transactions_finished' }).status)
      .toBe(TransactionsQueryStatus.QUERYING_TRANSACTIONS_FINISHED);
  });

  it('should reject an unknown status', () => {
    expect(UnifiedTransactionStatusData.safeParse({ ...payload, status: 'querying_transactions_lost' }).success)
      .toBe(false);
  });
});
