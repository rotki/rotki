import type { Ref } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useWrappedHistoryEvents } from '@/modules/statistics/wrapped/use-wrapped-history-events';

const mockGetEarliestEventTimestamp = vi.fn<() => Promise<number | undefined>>();
const mockIsFirstLoad = vi.fn<() => boolean>(() => false);
const mockSectionLoading = ref<boolean>(false);

const mockEventTaskLoading = ref<boolean>(false);
const mockProtocolCacheLoading = ref<boolean>(false);
const mockOnlineEventsLoading = ref<boolean>(false);

vi.mock('@/modules/history/events/use-history-events', () => ({
  useHistoryEvents: (): { getEarliestEventTimestamp: typeof mockGetEarliestEventTimestamp } => ({
    getEarliestEventTimestamp: mockGetEarliestEventTimestamp,
  }),
}));

vi.mock('@/modules/shell/sync-progress/use-status-updater', () => ({
  useStatusUpdater: (): { isFirstLoad: typeof mockIsFirstLoad; loading: Ref<boolean> } => ({
    isFirstLoad: mockIsFirstLoad,
    loading: mockSectionLoading,
  }),
}));

vi.mock('@/modules/core/tasks/use-task-store', () => ({
  useTaskStore: (): { useIsTaskRunning: (type: TaskType) => Ref<boolean> } => {
    const taskLoadingByType = new Map<TaskType, Ref<boolean>>([
      [TaskType.TRANSACTIONS_DECODING, mockEventTaskLoading],
      [TaskType.REFRESH_GENERAL_CACHE, mockProtocolCacheLoading],
      [TaskType.QUERY_ONLINE_EVENTS, mockOnlineEventsLoading],
    ]);
    return {
      useIsTaskRunning: (type: TaskType): Ref<boolean> => taskLoadingByType.get(type) ?? ref<boolean>(false),
    };
  },
}));

describe('useWrappedHistoryEvents', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    mockIsFirstLoad.mockReturnValue(false);
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
    mockIsFirstLoad.mockReturnValue(true);
    const { isFirstLoad } = useWrappedHistoryEvents(ref(0));
    expect(isFirstLoad()).toBe(true);
  });

  it('should be ready when not the first load and not refreshing', () => {
    mockIsFirstLoad.mockReturnValue(false);
    const { historyEventsReady } = useWrappedHistoryEvents(ref(0));
    expect(get(historyEventsReady)).toBe(true);
  });

  it('should not be ready during the first load', () => {
    mockIsFirstLoad.mockReturnValue(true);
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
    mockIsFirstLoad.mockReturnValue(false);
    mockGetEarliestEventTimestamp.mockResolvedValue(1_700_000_000);
    const start = ref<number>(0);
    useWrappedHistoryEvents(start);

    await vi.advanceTimersByTimeAsync(500);
    await vi.runAllTimersAsync();

    expect(mockGetEarliestEventTimestamp).toHaveBeenCalled();
    expect(get(start)).toBe(1_700_000_000);
  });
});
