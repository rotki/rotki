import type { ComputedRef } from 'vue';
import type { WorkStatus } from '@/modules/task-center/core/types';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWrappedHistoryEvents } from '@/modules/statistics/wrapped/use-wrapped-history-events';

const mockGetEarliestEventTimestamp = vi.fn<() => Promise<number | undefined>>();
// History freshness/liveness now come from the HISTORY_SYNC umbrella activity.
const mockHistoryEverCompleted = ref<boolean>(true);
const mockSectionLoading = ref<boolean>(false);

const mockEventTaskLoading = ref<boolean>(false);
const mockProtocolCacheLoading = ref<boolean>(false);
const mockOnlineEventsLoading = ref<boolean>(false);

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: (): { getEarliestEventTimestamp: typeof mockGetEarliestEventTimestamp } => ({
    getEarliestEventTimestamp: mockGetEarliestEventTimestamp,
  }),
}));

// Decoding runs native (TX_DECODING kind); online events run native (ONLINE_EVENTS kind, W7).
vi.mock('@/modules/task-center/use-task-center', () => ({
  useTaskCenter: (): Record<string, unknown> => ({
    useIsActive: (kind: string): ComputedRef<boolean> => computed<boolean>(() => {
      if (kind === 'history-sync')
        return get(mockSectionLoading);
      return kind === 'tx-decoding' ? get(mockEventTaskLoading) : false;
    }),
    useWorkStatus: (kind: string): ComputedRef<WorkStatus> => computed<WorkStatus>(() => {
      if (kind === 'history-sync') {
        const active = get(mockSectionLoading);
        return { active, everCompleted: get(mockHistoryEverCompleted), pending: false, running: active };
      }
      const active = kind === 'tx-decoding' ? get(mockEventTaskLoading) : false;
      return { active, everCompleted: false, pending: false, running: active };
    }),
    useIsActivePrefix: (kind: string): ComputedRef<boolean> => computed<boolean>(() =>
      kind === 'online-events' ? get(mockOnlineEventsLoading) : false),
    useWorkStatusPrefix: (kind: string): ComputedRef<WorkStatus> => computed<WorkStatus>(() => {
      const active = kind === 'online-events' ? get(mockOnlineEventsLoading) : false;
      return { active, everCompleted: false, pending: false, running: active };
    }),
  }),
}));

describe('useWrappedHistoryEvents', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    set(mockHistoryEverCompleted, true);
    mockGetEarliestEventTimestamp.mockResolvedValue(undefined);
    set(mockSectionLoading, false);
    set(mockEventTaskLoading, false);
    set(mockProtocolCacheLoading, false);
    set(mockOnlineEventsLoading, false);
  });

  it('should not be refreshing when nothing is loading', () => {
    const { refreshing } = useWrappedHistoryEvents(ref(0));
    expect(get(refreshing)).toBe(false);
  });

  it('should be refreshing when the section is loading', () => {
    set(mockSectionLoading, true);
    const { refreshing } = useWrappedHistoryEvents(ref(0));
    expect(get(refreshing)).toBe(true);
  });

  it('should be refreshing when any related task is running', () => {
    set(mockOnlineEventsLoading, true);
    const { refreshing } = useWrappedHistoryEvents(ref(0));
    expect(get(refreshing)).toBe(true);
  });

  it('should expose the first load state', () => {
    set(mockHistoryEverCompleted, false);
    const { isFirstLoad } = useWrappedHistoryEvents(ref(0));
    expect(isFirstLoad()).toBe(true);
  });

  it('should be ready when not the first load and not refreshing', () => {
    set(mockHistoryEverCompleted, true);
    const { historyEventsReady } = useWrappedHistoryEvents(ref(0));
    expect(get(historyEventsReady)).toBe(true);
  });

  it('should not be ready during the first load', () => {
    set(mockHistoryEverCompleted, false);
    const { historyEventsReady } = useWrappedHistoryEvents(ref(0));
    expect(get(historyEventsReady)).toBe(false);
  });

  it('should set the start from the earliest event when it exists', async () => {
    mockGetEarliestEventTimestamp.mockResolvedValue(1_600_000_000);
    const start = ref<number>(0);
    const { initializeStartFromEarliestEvent } = useWrappedHistoryEvents(start);
    await initializeStartFromEarliestEvent();
    expect(get(start)).toBe(1_600_000_000);
  });

  it('should leave the start unchanged when there is no earliest event', async () => {
    mockGetEarliestEventTimestamp.mockResolvedValue(undefined);
    const start = ref<number>(0);
    const { initializeStartFromEarliestEvent } = useWrappedHistoryEvents(start);
    await initializeStartFromEarliestEvent();
    expect(get(start)).toBe(0);
  });

  it('should initialize the start when the debounced ready state turns true', async () => {
    vi.useFakeTimers();
    set(mockHistoryEverCompleted, true);
    mockGetEarliestEventTimestamp.mockResolvedValue(1_700_000_000);
    const start = ref<number>(0);
    useWrappedHistoryEvents(start);

    await vi.advanceTimersByTimeAsync(500);
    await vi.runAllTimersAsync();

    expect(mockGetEarliestEventTimestamp).toHaveBeenCalled();
    expect(get(start)).toBe(1_700_000_000);
  });
});
