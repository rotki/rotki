import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref, shallowRef } from 'vue';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useHistoryEventsAutoFetch } from './use-history-events-auto-fetch';

const SETTLE_QUIET = 2000;
const SUSTAINED_MAX_WAIT = 20_000;

interface FakeActivity {
  kind: ActivityKind;
}

const activeActivities = shallowRef<FakeActivity[]>([]);

/**
 * Read lazily: `vi.mock` is hoisted above the ref, so the factory can only close over a function
 * that resolves it at call time, not the ref itself.
 */
function currentActive(): Ref<FakeActivity[]> {
  return activeActivities;
}

vi.mock('@/modules/task-center/use-task-center', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/task-center/use-task-center')>();
  return {
    ...actual,
    useTaskCenter: (): { active: Ref<FakeActivity[]> } => ({ active: currentActive() }),
  };
});

interface MountedAutoFetch {
  wrapper: VueWrapper;
  markStale: () => void;
}

function mountAutoFetch(
  shouldFetch: Ref<boolean>,
  onProgress: () => Promise<void>,
  onSettle: () => Promise<void> = vi.fn().mockResolvedValue(undefined),
): MountedAutoFetch {
  let markStale: () => void = () => {};
  const wrapper = mount(defineComponent({
    render: () => null,
    setup() {
      ({ markStale } = useHistoryEventsAutoFetch(shouldFetch, { onProgress, onSettle }));
      return {};
    },
  }));
  return { markStale, wrapper };
}

/** Put `count` event-producing activities in flight, the way a producer's submit does. */
function startProducers(count: number, kind: ActivityKind = ActivityKind.TX_SYNC): void {
  set(activeActivities, Array.from({ length: count }, (): FakeActivity => ({ kind })));
}

/** Finish one of them. This is the signal: a unit of work completed, so its rows exist. */
function finishOne(): void {
  set(activeActivities, get(activeActivities).slice(1));
}

describe('useHistoryEventsAutoFetch', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(activeActivities, []);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should not fetch while no work is running', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    mountAutoFetch(ref(true), onProgress);

    await vi.advanceTimersByTimeAsync(SUSTAINED_MAX_WAIT * 2);

    expect(onProgress).not.toHaveBeenCalled();
  });

  it('should not fetch when work merely starts', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    mountAutoFetch(ref(true), onProgress);

    // Submitting work produces no rows, so there is nothing to show yet.
    startProducers(3);
    await vi.advanceTimersByTimeAsync(SETTLE_QUIET + 100);

    expect(onProgress).not.toHaveBeenCalled();
  });

  it('should fetch once an activity finishes', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    mountAutoFetch(ref(true), onProgress);

    startProducers(2);
    await vi.advanceTimersByTimeAsync(10);
    finishOne();
    await vi.advanceTimersByTimeAsync(SETTLE_QUIET + 100);

    expect(onProgress).toHaveBeenCalledTimes(1);
  });

  it('should read once for a burst of completions', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    mountAutoFetch(ref(true), onProgress);

    // A chain finishing retires its addresses together; they are worth one read, not one each.
    startProducers(6);
    await vi.advanceTimersByTimeAsync(10);
    for (let i = 0; i < 5; i++) {
      finishOne();
      await vi.advanceTimersByTimeAsync(100);
    }
    await vi.advanceTimersByTimeAsync(SETTLE_QUIET + 100);

    expect(onProgress).toHaveBeenCalledTimes(1);
  });

  it('should still read during a long run of steady completions', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    mountAutoFetch(ref(true), onProgress);

    // maxWait means a run that never goes quiet does not starve the table.
    startProducers(30);
    await vi.advanceTimersByTimeAsync(10);
    for (let i = 0; i < 25; i++) {
      finishOne();
      await vi.advanceTimersByTimeAsync(1000);
    }

    expect(onProgress).toHaveBeenCalled();
  });

  it('should not fetch when the flag is off', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    mountAutoFetch(ref(false), onProgress);

    startProducers(2);
    await vi.advanceTimersByTimeAsync(10);
    finishOne();
    await vi.advanceTimersByTimeAsync(SETTLE_QUIET + 100);

    expect(onProgress).not.toHaveBeenCalled();
  });

  it('should ignore activities that cannot produce events', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    mountAutoFetch(ref(true), onProgress);

    // A balance refresh finishing is not a reason to re-read the events table.
    startProducers(2, ActivityKind.BLOCKCHAIN_BALANCES);
    await vi.advanceTimersByTimeAsync(10);
    finishOne();
    await vi.advanceTimersByTimeAsync(SETTLE_QUIET + 100);

    expect(onProgress).not.toHaveBeenCalled();
  });

  it('should read the locations once when the run finishes', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    const onSettle = vi.fn().mockResolvedValue(undefined);
    const shouldFetch = ref(true);
    mountAutoFetch(shouldFetch, onProgress, onSettle);

    set(shouldFetch, false);
    await vi.advanceTimersByTimeAsync(100);

    expect(onSettle).toHaveBeenCalledTimes(1);
    expect(onProgress).not.toHaveBeenCalled();
  });

  it('should read once when a completion and an event modification arrive together', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    const { markStale } = mountAutoFetch(ref(true), onProgress);

    // Both signals share one debounce; two of them used to land on the same instant and read the
    // identical page twice.
    startProducers(2);
    await vi.advanceTimersByTimeAsync(10);
    finishOne();
    markStale();
    await vi.advanceTimersByTimeAsync(SETTLE_QUIET + 100);

    expect(onProgress).toHaveBeenCalledTimes(1);
  });

  it('should read on an event modification while nothing is running', async () => {
    const onProgress = vi.fn().mockResolvedValue(undefined);
    const { markStale } = mountAutoFetch(ref(true), onProgress);

    markStale();
    await vi.advanceTimersByTimeAsync(SETTLE_QUIET + 100);

    expect(onProgress).toHaveBeenCalledTimes(1);
  });
});
