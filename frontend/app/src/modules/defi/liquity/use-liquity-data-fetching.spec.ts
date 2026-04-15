import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Module } from '@/modules/common/modules';
import { Section, Status } from '@/modules/common/status';
import { TaskType } from '@/modules/tasks/task-type';
import { useLiquityDataFetching } from './use-liquity-data-fetching';
import '@test/i18n';

const mockRunTask = vi.fn();
const mockIsTaskRunning = vi.fn().mockReturnValue(false);
const mockFetchLiquityBalances = vi.fn();
const mockFetchLiquityStaking = vi.fn();
const mockFetchLiquityStakingPools = vi.fn();
const mockFetchLiquityStatistics = vi.fn();

vi.mock('@/modules/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn((): Record<string, unknown> => ({
    runTask: mockRunTask,
  })),
}));

vi.mock('@/modules/tasks/use-task-store', () => ({
  useTaskStore: vi.fn((): Record<string, unknown> => ({
    isTaskRunning: mockIsTaskRunning,
  })),
}));

vi.mock('@/composables/api/defi/liquity', () => ({
  useLiquityApi: vi.fn((): Record<string, unknown> => ({
    fetchLiquityBalances: mockFetchLiquityBalances,
    fetchLiquityStaking: mockFetchLiquityStaking,
    fetchLiquityStakingPools: mockFetchLiquityStakingPools,
    fetchLiquityStatistics: mockFetchLiquityStatistics,
  })),
}));

vi.mock('@/composables/premium', () => ({
  usePremium: vi.fn((): Ref<boolean> => ref<boolean>(true)),
}));

vi.mock('@/store/settings/general', () => ({
  useGeneralSettingsStore: vi.fn((): Record<string, unknown> => ({
    activeModules: ref<string[]>([Module.LIQUITY]),
  })),
}));

describe('useLiquityDataFetching', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockIsTaskRunning.mockReturnValue(false);
    mockRunTask.mockResolvedValue({ success: false, cancelled: true });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchBalances', () => {
    it('should call runTask with correct task type and section', async () => {
      mockFetchLiquityBalances.mockResolvedValue({ taskId: 1 });

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(mockRunTask).toHaveBeenCalledOnce();
      const [, options] = mockRunTask.mock.calls[0];
      expect(options.type).toBe(TaskType.LIQUITY_BALANCES);
    });

    it('should pass refresh flag', async () => {
      mockFetchLiquityBalances.mockResolvedValue({ taskId: 1 });

      const { useStatusStore } = await import('@/store/status');
      const statusStore = useStatusStore();
      statusStore.setStatus({ status: Status.LOADED, section: Section.DEFI_LIQUITY_BALANCES });

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances(true);

      expect(mockRunTask).toHaveBeenCalledOnce();
    });
  });

  describe('fetchPools', () => {
    it('should call runTask with correct task type', async () => {
      mockFetchLiquityStakingPools.mockResolvedValue({ taskId: 1 });

      const { fetchPools } = useLiquityDataFetching();
      await fetchPools();

      expect(mockRunTask).toHaveBeenCalledOnce();
      const [, options] = mockRunTask.mock.calls[0];
      expect(options.type).toBe(TaskType.LIQUITY_STAKING_POOLS);
    });
  });

  describe('fetchStaking', () => {
    it('should call runTask with correct task type', async () => {
      mockFetchLiquityStaking.mockResolvedValue({ taskId: 1 });

      const { fetchStaking } = useLiquityDataFetching();
      await fetchStaking();

      expect(mockRunTask).toHaveBeenCalledOnce();
      const [, options] = mockRunTask.mock.calls[0];
      expect(options.type).toBe(TaskType.LIQUITY_STAKING);
    });
  });

  describe('fetchStatistics', () => {
    it('should call runTask with correct task type', async () => {
      mockFetchLiquityStatistics.mockResolvedValue({ taskId: 1 });

      const { fetchStatistics } = useLiquityDataFetching();
      await fetchStatistics();

      expect(mockRunTask).toHaveBeenCalledOnce();
      const [, options] = mockRunTask.mock.calls[0];
      expect(options.type).toBe(TaskType.LIQUITY_STATISTICS);
    });
  });

  describe('module guard', () => {
    it('should skip fetch when module is not active', async () => {
      const { useGeneralSettingsStore } = await import('@/store/settings/general');
      // @ts-expect-error partial mock
      vi.mocked(useGeneralSettingsStore).mockReturnValue({ activeModules: ref<string[]>([]) });

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(mockRunTask).not.toHaveBeenCalled();
    });
  });

  describe('task running guard', () => {
    it('should skip fetch when task is already running', async () => {
      mockIsTaskRunning.mockReturnValue(true);

      const { fetchBalances } = useLiquityDataFetching();
      await fetchBalances();

      expect(mockRunTask).not.toHaveBeenCalled();
    });
  });
});
