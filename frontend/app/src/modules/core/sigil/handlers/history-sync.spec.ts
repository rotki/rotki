import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockFetchHistoryEvents = vi.fn();

vi.mock('@/modules/history/api/events/use-history-events-api', () => ({
  useHistoryEventsApi: vi.fn(() => ({
    fetchHistoryEvents: mockFetchHistoryEvents,
  })),
}));

const { useHistorySyncHandler } = await import('@/modules/core/sigil/handlers/history-sync');

describe('useHistorySyncHandler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockFetchHistoryEvents.mockReset();
  });

  it('should return total, spam, and group counts', async () => {
    mockFetchHistoryEvents
      .mockResolvedValueOnce({ entriesTotal: 42, entriesFound: 35 })
      .mockResolvedValueOnce({ entriesFound: 20 });

    const collect = useHistorySyncHandler();
    const result = await collect();

    expect(result).toEqual({ premium: false, plan: 'Free', totalEvents: 42, spamEvents: 7, totalGroups: 20 });
    expect(mockFetchHistoryEvents).toHaveBeenCalledTimes(2);
    expect(mockFetchHistoryEvents).toHaveBeenCalledWith({
      limit: 1,
      offset: 0,
      aggregateByGroupIds: false,
      excludeIgnoredAssets: true,
    });
    expect(mockFetchHistoryEvents).toHaveBeenCalledWith({
      limit: 1,
      offset: 0,
      aggregateByGroupIds: true,
      excludeIgnoredAssets: true,
    });
  });

  it('should return undefined on failure', async () => {
    mockFetchHistoryEvents.mockRejectedValueOnce(new Error('network'));

    const collect = useHistorySyncHandler();
    const result = await collect();

    expect(result).toBeUndefined();
  });
});
