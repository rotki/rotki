import { describe, expect, it } from 'vitest';
import { TransactionsQueryStatus, UnifiedTransactionStatusData } from './status-types';

// The seam: what a `transaction_status` payload parses to. The backend ends a query no indexer
// could serve with `querying_transactions_failed`, and the rest of the frontend only knows
// `FAILED`, so the schema is the one place the two have to meet.
describe('unifiedTransactionStatusData', () => {
  const payload = {
    address: '0x123',
    chain: 'base',
    period: [0, 1000],
    subtype: 'evm',
  };

  it('should fold the backend failed status into FAILED', () => {
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
