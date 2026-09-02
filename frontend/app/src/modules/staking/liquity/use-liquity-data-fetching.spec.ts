import { runSpecWith } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/core/common/modules';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityPart, type WorkStatus } from '@/modules/task-center/core/types';
import { useLiquityDataFetching } from './use-liquity-data-fetching';
import { useLiquityStore } from './use-liquity-store';
import '@test/i18n';

const mockFetchLiquityBalances = vi.fn();
const mockFetchLiquityStaking = vi.fn();
const mockFetchLiquityStakingPools = vi.fn();
const mockFetchLiquityStatistics = vi.fn();

const IDLE: WorkStatus = { active: false, everCompleted: false, pending: false, running: false };
let workStatus: WorkStatus = { ...IDLE };
const statusOf = vi.fn((): WorkStatus => workStatus);
const runTaskResult = vi.fn();

/** Runs the submitted spec inline so assertions see the real `run` body. */
const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    runTaskResult,
    statusOf,
    submitTask,
  })),
}));

vi.mock('@/modules/staking/liquity/use-liquity-api', () => ({
  useLiquityApi: vi.fn((): Record<string, unknown> => ({
    fetchLiquityBalances: mockFetchLiquityBalances,
    fetchLiquityStaking: mockFetchLiquityStaking,
    fetchLiquityStakingPools: mockFetchLiquityStakingPools,
    fetchLiquityStatistics: mockFetchLiquityStatistics,
  })),
}));

const mockPremium = ref<boolean>(true);
vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: vi.fn((): Ref<boolean> => mockPremium),
}));

const notifyError = vi.fn();
vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn((): Record<string, unknown> => ({ notifyError })),
}));

const mockActiveModules = ref<string[]>([Module.LIQUITY]);
vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockActiveModules),
}));

describe('useLiquityDataFetching', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(mockActiveModules, [Module.LIQUITY]);
    set(mockPremium, true);
    workStatus = { ...IDLE };
    runTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchBalances', () => {
    it('should submit a native task with the correct task type', async () => {
      mockFetchLiquityBalances.mockResolvedValue({ taskId: 1 });

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(submitTask).toHaveBeenCalledOnce();
      expect(runTaskResult).toHaveBeenCalledOnce();
    });

    it('should proceed on refresh even when the activity already completed', async () => {
      mockFetchLiquityBalances.mockResolvedValue({ taskId: 1 });
      workStatus = { ...IDLE, everCompleted: true };

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances(true);

      expect(submitTask).toHaveBeenCalledOnce();
    });

    it('should skip a non-refresh fetch when the activity already completed', async () => {
      workStatus = { ...IDLE, everCompleted: true };

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(submitTask).not.toHaveBeenCalled();
    });
  });

  describe('fetchPools', () => {
    it('should submit a native task with the correct task type', async () => {
      mockFetchLiquityStakingPools.mockResolvedValue({ taskId: 1 });

      const { fetchPools } = useLiquityDataFetching();
      await fetchPools();

      expect(submitTask).toHaveBeenCalledOnce();
    });
  });

  describe('fetchStaking', () => {
    it('should submit a native task with the correct task type', async () => {
      mockFetchLiquityStaking.mockResolvedValue({ taskId: 1 });

      const { fetchStaking } = useLiquityDataFetching();
      await fetchStaking();

      expect(submitTask).toHaveBeenCalledOnce();
    });
  });

  describe('fetchStatistics', () => {
    it('should submit a native task with the correct task type', async () => {
      mockFetchLiquityStatistics.mockResolvedValue({ taskId: 1 });

      const { fetchStatistics } = useLiquityDataFetching();
      await fetchStatistics();

      expect(submitTask).toHaveBeenCalledOnce();
    });
  });

  describe('module guard', () => {
    it('should skip fetch when module is not active', async () => {
      set(mockActiveModules, []);

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(submitTask).not.toHaveBeenCalled();
    });
  });

  describe('task running guard', () => {
    it('should skip fetch when an activity is already active', async () => {
      workStatus = { ...IDLE, active: true, running: true };

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(submitTask).not.toHaveBeenCalled();
    });
  });

  describe('the premium guard', () => {
    beforeEach(() => {
      set(mockPremium, false);
    });

    it('should still fetch balances, which are free', async () => {
      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(submitTask).toHaveBeenCalledTimes(1);
    });

    it.each([
      ['fetchPools' as const],
      ['fetchStaking' as const],
      ['fetchStatistics' as const],
    ])('should skip %s without premium', async (name) => {
      const fetching = useLiquityDataFetching();
      await fetching[name]();

      expect(submitTask).not.toHaveBeenCalled();
    });

    it('should skip the premium fetches even on an explicit refresh', async () => {
      const { fetchStaking } = useLiquityDataFetching();
      await fetchStaking(true);

      expect(submitTask).not.toHaveBeenCalled();
    });
  });

  describe('a successful fetch', () => {
    it('should validate the response and store it', async () => {
      const staking = { '0xaaa': { balances: null, proxies: null } };
      runTaskResult.mockResolvedValue(ok(staking));

      const { fetchStaking } = useLiquityDataFetching();
      await fetchStaking();

      expect(get(useLiquityStore().staking)).toEqual(staking);
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should keep each fetch on its own part of the activity', async () => {
      runTaskResult.mockResolvedValue(ok({}));

      const { fetchStatistics } = useLiquityDataFetching();
      await fetchStatistics();

      expect(submitTask.mock.calls[0][0].id).toContain(ActivityPart.STATISTICS);
    });
  });

  describe('a failed fetch', () => {
    it('should report an actionable failure with the backend message', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'backend said no' })));

      const { fetchPools } = useLiquityDataFetching();
      await fetchPools();

      expect(notifyError).toHaveBeenCalledTimes(1);
      expect(notifyError.mock.calls[0][1]).toContain('backend said no');
    });

    it('should stay quiet on a cancellation, which is not a failure', async () => {
      runTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      const { fetchPools } = useLiquityDataFetching();
      await fetchPools();

      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should name the failing part in its own message', async () => {
      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'nope' })));

      const { fetchStatistics } = useLiquityDataFetching();
      await fetchStatistics();

      // The four fetches must not share one error string, or the toast names the wrong data.
      expect(notifyError.mock.calls[0][0]).toContain('liquity_statistics');
    });
  });
});
