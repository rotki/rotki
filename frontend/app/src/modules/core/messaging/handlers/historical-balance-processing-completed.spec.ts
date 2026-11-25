import { get } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { WebsocketMessage } from '@/modules/core/messaging/messages';
import { SocketMessageType } from '@/modules/core/messaging/types/base';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { createHistoricalBalanceProcessingCompletedHandler } from './historical-balance-processing-completed';

const mockSyncCostBasisStalled = vi.fn();

vi.mock('@/modules/task-center/background/use-background-tasks', () => ({
  useBackgroundTasks: (): { syncCostBasisStalled: typeof mockSyncCostBasisStalled } => ({
    syncCostBasisStalled: mockSyncCostBasisStalled,
  }),
}));

describe('createHistoricalBalanceProcessingCompletedHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockSyncCostBasisStalled.mockClear();
  });

  it('should notify completion and pass costBasisStalled when present', async () => {
    const store = useHistoricalBalanceProcessingStore();
    const handler = createHistoricalBalanceProcessingCompletedHandler();
    const costBasisStalled = { reason: 'rate_limited', since: 1_700_000_000 };
    const parsed = WebsocketMessage.parse({
      data: { costBasisStalled },
      type: SocketMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED,
    });

    await handler.handle(parsed.data);

    expect(get(store.historicalBalanceProcessingCompleted)).toBe(1);
    expect(mockSyncCostBasisStalled).toHaveBeenCalledWith(costBasisStalled);
  });

  it('should clear costBasisStalled when omitted on a clean completion', async () => {
    const store = useHistoricalBalanceProcessingStore();
    const handler = createHistoricalBalanceProcessingCompletedHandler();
    const parsed = WebsocketMessage.parse({
      data: {},
      type: SocketMessageType.HISTORICAL_BALANCE_PROCESSING_COMPLETED,
    });

    await handler.handle(parsed.data);

    expect(get(store.historicalBalanceProcessingCompleted)).toBe(1);
    expect(mockSyncCostBasisStalled).toHaveBeenCalledWith(undefined);
  });
});
