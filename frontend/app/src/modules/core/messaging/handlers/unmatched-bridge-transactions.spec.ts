import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createUnmatchedBridgeTransactionsHandler } from '@/modules/core/messaging/handlers/unmatched-bridge-transactions';

const { fetchUnmatchedBridgeTransactions } = vi.hoisted(() => ({
  fetchUnmatchedBridgeTransactions: vi.fn<(onlyIgnored?: boolean) => Promise<void>>(),
}));

vi.mock('@/modules/history/events/use-unmatched-bridge-transactions', () => ({
  useUnmatchedBridgeTransactions: (): object => ({ fetchUnmatchedBridgeTransactions }),
}));

describe('createUnmatchedBridgeTransactionsHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchUnmatchedBridgeTransactions.mockResolvedValue();
  });

  it('should re-read the unmatched legs the row counts and create no notification', async () => {
    const handler = createUnmatchedBridgeTransactionsHandler();

    const result = await handler.handle({ count: 3 });

    expect(result).toBeNull();
    expect(fetchUnmatchedBridgeTransactions).toHaveBeenCalledExactlyOnceWith();
  });

  it('should re-read on a zero count too, so a row raised before goes away', async () => {
    const handler = createUnmatchedBridgeTransactionsHandler();

    await handler.handle({ count: 0 });

    expect(fetchUnmatchedBridgeTransactions).toHaveBeenCalledOnce();
  });
});
