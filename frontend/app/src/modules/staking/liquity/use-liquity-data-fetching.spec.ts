import type { WorkStatus } from '@/modules/task-center/core/types';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { err } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/core/common/modules';
import { Cancelled } from '@/modules/core/tasks/task-result';
import { useLiquityDataFetching } from './use-liquity-data-fetching';
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

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: vi.fn((): Ref<boolean> => ref<boolean>(true)),
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
    workStatus = { ...IDLE };
    // Default to a cancelled outcome so the success mapper (schema parse) never runs unless a test
    // opts in; a cancellation is non-actionable, so it also asserts no error notification.
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
});
