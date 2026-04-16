import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useEthValidatorFetching } from '@/modules/staking/eth/use-eth-validator-fetching';

const mockGetEth2Validators = vi.fn();

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    getEth2Validators: mockGetEth2Validators,
  })),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: vi.fn(() => ({
    getNativeAsset: vi.fn((): string => 'ETH2'),
  })),
}));

const mockUpdateAccounts = vi.fn();

vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: vi.fn(() => ({
    updateAccounts: mockUpdateAccounts,
  })),
}));

const mockNotifyError = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
  })),
}));

const mockRunTask = vi.fn();

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  isActionableFailure: vi.fn((outcome: TaskResult<unknown>): boolean =>
    !outcome.success && !('cancelled' in outcome && outcome.cancelled) && !('skipped' in outcome && outcome.skipped),
  ),
  useTaskHandler: vi.fn(() => ({
    runTask: mockRunTask,
  })),
}));

const mockIsEth2Enabled = vi.fn((): boolean => false);
const mockStakingValidatorsLimits = ref<{ limit: number; total: number }>();

vi.mock('@/modules/staking/use-blockchain-validators-store', () => ({
  useBlockchainValidatorsStore: vi.fn(() => {
    const store = reactive({
      isEth2Enabled: mockIsEth2Enabled,
      stakingValidatorsLimits: mockStakingValidatorsLimits,
    });
    return store;
  }),
}));

describe('useEthValidatorFetching', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsEth2Enabled.mockReturnValue(false);
    set(mockStakingValidatorsLimits, undefined);
  });

  describe('fetchEthStakingValidators', () => {
    it('should skip fetch when eth2 is not enabled', async () => {
      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(mockRunTask).not.toHaveBeenCalled();
    });

    it('should fetch and update accounts on success', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      const mockValidators = {
        entries: [{ index: 1, publicKey: '0xabc', status: 'active' }],
        entriesFound: 1,
        entriesLimit: 100,
      };

      mockRunTask.mockResolvedValue({
        result: mockValidators,
        success: true,
      });

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(mockRunTask).toHaveBeenCalledOnce();
      expect(mockUpdateAccounts).toHaveBeenCalledOnce();
    });

    it('should update staking validators limits on success', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      mockRunTask.mockResolvedValue({
        result: {
          entries: [],
          entriesFound: 50,
          entriesLimit: 100,
        },
        success: true,
      });

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(get(mockStakingValidatorsLimits)).toEqual({ limit: 100, total: 50 });
    });

    it('should notify on actionable failure', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      mockRunTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: false,
        error: new Error('Network error'),
        message: 'Network error',
        skipped: false,
        success: false,
      });

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mockUpdateAccounts).not.toHaveBeenCalled();
    });

    it('should not notify on cancelled task', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      mockRunTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: true,
        message: 'cancelled',
        skipped: false,
        success: false,
      });

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should pass filter payload to API', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      mockRunTask.mockImplementation(async (fn: () => Promise<unknown>) => {
        await fn();
        return {
          result: { entries: [], entriesFound: 0, entriesLimit: 100 },
          success: true,
        };
      });

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators({ ignoreCache: true });

      expect(mockGetEth2Validators).toHaveBeenCalledWith({ ignoreCache: true });
    });
  });
});
