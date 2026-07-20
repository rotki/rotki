import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed } from 'vue';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';

const state = vi.hoisted((): { processing: boolean } => ({ processing: false }));

vi.mock('@/modules/history/events/tx/use-history-transaction-decoding', () => ({
  useHistoryTransactionDecoding: (): Record<string, unknown> => ({
    fetchUndecodedTransactionsBreakdown: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): Record<string, unknown> => ({
    processing: computed(() => state.processing),
  }),
}));

describe('useUndecodedTransactionsCount', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    state.processing = false;
  });

  it('should sum the leftover undecoded transactions across chains', () => {
    const store = useDecodingStatusStore();
    store.setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });
    store.setUndecodedTransactionsStatus({ chain: 'optimism', processed: 5, total: 8 });

    const { undecodedCount } = useUndecodedTransactionsCount();
    expect(get(undecodedCount)).toBe(11); // (10-2) + (8-5)
  });

  it('should clamp negative differences to zero', () => {
    const store = useDecodingStatusStore();
    store.setUndecodedTransactionsStatus({ chain: 'eth', processed: 12, total: 10 });

    const { undecodedCount } = useUndecodedTransactionsCount();
    expect(get(undecodedCount)).toBe(0);
  });

  it('should suppress the count while history is processing (default status)', () => {
    state.processing = true;
    const store = useDecodingStatusStore();
    store.setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });

    const { undecodedCount } = useUndecodedTransactionsCount();
    expect(get(undecodedCount)).toBe(0);
  });

  it('should honour a processing override over the shared status', () => {
    state.processing = false; // shared status says idle
    const store = useDecodingStatusStore();
    store.setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });

    const { undecodedCount } = useUndecodedTransactionsCount(() => true);
    expect(get(undecodedCount)).toBe(0);
  });

  it('should count when the override says not processing even if status is processing', () => {
    state.processing = true; // shared status says busy
    const store = useDecodingStatusStore();
    store.setUndecodedTransactionsStatus({ chain: 'eth', processed: 2, total: 10 });

    const { undecodedCount } = useUndecodedTransactionsCount(() => false);
    expect(get(undecodedCount)).toBe(8);
  });
});
