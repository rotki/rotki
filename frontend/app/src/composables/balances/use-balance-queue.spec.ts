import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComputedRef, nextTick, ref } from 'vue';
import { BalanceQueueService } from '@/services/balance-queue';

const mockAnyEventsDecoding = ref<boolean>(false);

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: vi.fn((): { anyEventsDecoding: ComputedRef<boolean> } => ({
    anyEventsDecoding: computed<boolean>(() => get(mockAnyEventsDecoding)),
  })),
}));

const { useBalanceQueue } = await import('@/composables/balances/use-balance-queue');

describe('useBalanceQueue', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    BalanceQueueService.resetInstance();
    set(mockAnyEventsDecoding, false);
  });

  it('should process token detection items', async () => {
    const { queueTokenDetection, stats } = useBalanceQueue();

    const fetchFn = vi.fn().mockResolvedValue(undefined);
    await queueTokenDetection('eth', ['0x123'], fetchFn);

    expect(fetchFn).toHaveBeenCalledWith('0x123');
    await nextTick();
    expect(get(stats).completed).toBe(1);
  });

  it('should process balance query items', async () => {
    const { queueBalanceQueries, stats } = useBalanceQueue();

    const fetchFn = vi.fn().mockResolvedValue(undefined);
    await queueBalanceQueries(['eth', 'btc'], fetchFn);

    expect(fetchFn).toHaveBeenCalledWith('eth');
    expect(fetchFn).toHaveBeenCalledWith('btc');
    await nextTick();
    expect(get(stats).completed).toBe(2);
  });

  it('should reset state when singleton is reset between sessions', async () => {
    const { queueBalanceQueries, stats } = useBalanceQueue();

    // Session 1: process some items
    const fetchFn = vi.fn().mockResolvedValue(undefined);
    await queueBalanceQueries(['eth', 'btc'], fetchFn);
    await nextTick();
    expect(get(stats).completed).toBe(2);
    expect(get(stats).total).toBe(2);

    // Simulate logout: reset the singleton (as useSessionStateCleaner does)
    BalanceQueueService.resetInstance();

    // Session 2: get a fresh composable (simulates re-login)
    const session2 = useBalanceQueue();

    // Stats should be clean — no stale data from session 1
    expect(get(session2.stats).completed).toBe(0);
    expect(get(session2.stats).total).toBe(0);
    expect(get(session2.stats).failed).toBe(0);

    // Should be able to process items on the new queue
    const fetchFn2 = vi.fn().mockResolvedValue(undefined);
    await session2.queueTokenDetection('eth', ['0xabc'], fetchFn2);

    expect(fetchFn2).toHaveBeenCalledWith('0xabc');
    await nextTick();
    expect(get(session2.stats).completed).toBe(1);
    expect(get(session2.stats).total).toBe(1);
  });

  it('should block processing while events are decoding', async () => {
    set(mockAnyEventsDecoding, true);

    const { queueTokenDetection, stats } = useBalanceQueue();

    const fetchFn = vi.fn().mockResolvedValue(undefined);
    const promise = queueTokenDetection('eth', ['0x123'], fetchFn);

    // Advance past the 500ms polling interval so updateSharedState() fires
    await vi.advanceTimersByTimeAsync(500);

    // Should be blocked — item is pending, not executed
    expect(fetchFn).not.toHaveBeenCalled();
    expect(get(stats).pending).toBe(1);

    // Unblock by finishing decoding
    set(mockAnyEventsDecoding, false);
    await nextTick();

    await promise;

    expect(fetchFn).toHaveBeenCalledWith('0x123');
    await nextTick();
    expect(get(stats).completed).toBe(1);
  });
});
