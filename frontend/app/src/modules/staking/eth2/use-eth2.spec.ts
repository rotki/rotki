import { runSpecWith } from '@test/utils/mocks/native-task';
import flushPromises from 'flush-promises';
import { ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremium } from '@/modules/premium/use-premium';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useEth2Staking } from '@/modules/staking/eth2/use-eth2';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';

const runTaskResult = vi.fn().mockResolvedValue(ok(undefined));
/** Runs the submitted spec inline so assertions see the real `run` body. */
const submitTask = vi.fn(runSpecWith(runTaskResult));
const statusOf = vi.fn(() => ({ active: false, everCompleted: false }));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    runTaskResult,
    statusOf,
    submitTask,
  })),
}));

describe('useEth2Staking', () => {
  beforeEach(() => {
    // Per-test instance: created in the describe body it would be shared, letting store state leak
    // between cases.
    setActivePinia(createPinia());
    const premium = usePremium();
    set(premium, true);
    vi.clearAllMocks();
    statusOf.mockReturnValue({ active: false, everCompleted: false });
  });

  describe('refreshPerformance', () => {
    it('should mark the performance refresh stale once a validator is added', async () => {
      const { refreshPerformance } = useEth2Staking();
      await refreshPerformance(false);

      expect(submitTask).toHaveBeenCalledTimes(1);
      expect(submitTask.mock.calls[0][0]).toMatchObject({
        id: makeActivityId(ActivityKind.STAKING, ActivityPart.PERFORMANCE),
        staleAfter: [{ kind: ActivityKind.STAKING, parts: [ActivityPart.ADD] }],
      });
    });

    it('should skip a background refresh that has already completed once', async () => {
      statusOf.mockReturnValue({ active: false, everCompleted: true });
      const { refreshPerformance } = useEth2Staking();
      await refreshPerformance(false);

      expect(submitTask).not.toHaveBeenCalled();
    });

    it('should still run a user-initiated refresh after one has completed', async () => {
      statusOf.mockReturnValue({ active: false, everCompleted: true });
      const { refreshPerformance } = useEth2Staking();
      await refreshPerformance(true);

      expect(submitTask).toHaveBeenCalledTimes(1);
    });
  });

  describe('fetchPerformance', () => {
    it('should fetch limited validators based on static limit and ignore global limit', async () => {
      const { fetchPerformance, performance, pagination } = useEth2Staking();
      await fetchPerformance({ limit: 10, offset: 0 });

      expect(get(performance).validators).toHaveLength(10);
      expect(get(performance).entriesTotal).toBe(11);

      const itemsPerPage = useItemsPerPage();

      set(itemsPerPage, 25);
      set(pagination, { ...get(pagination), offset: 10 });

      await flushPromises();
      await nextTick();

      expect(get(pagination).limit).toBe(10);

      set(itemsPerPage, 50);

      expect(get(pagination).limit).toBe(10);
    });
  });
});
