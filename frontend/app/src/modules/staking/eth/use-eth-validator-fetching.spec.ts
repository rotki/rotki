import { runSpecWith } from '@test/utils/mocks/native-task';
import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Cancelled, TaskFailed } from '@/modules/core/tasks/task-result';
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

const runTaskResult = vi.fn();
/** Runs the submitted spec inline so assertions see the real `run` body. */
const submitTask = vi.fn(runSpecWith(runTaskResult));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: vi.fn(() => ({
    cancelByType: vi.fn(() => vi.fn()),
    runTaskResult,
    statusOf: vi.fn(),
    submitTask,
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

      expect(submitTask).not.toHaveBeenCalled();
    });

    it('should fetch and update accounts on success', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      const mockValidators = {
        entries: [{ index: 1, publicKey: '0xabc', status: 'active' }],
        entriesFound: 1,
        entriesLimit: 100,
      };

      runTaskResult.mockResolvedValue(ok(mockValidators));

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(submitTask).toHaveBeenCalledOnce();
      expect(mockUpdateAccounts).toHaveBeenCalledOnce();
    });

    it('should update staking validators limits on success', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      runTaskResult.mockResolvedValue(ok({
        entries: [],
        entriesFound: 50,
        entriesLimit: 100,
      }));

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(get(mockStakingValidatorsLimits)).toEqual({ limit: 100, total: 50 });
    });

    it('should notify on actionable failure', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      runTaskResult.mockResolvedValue(err(TaskFailed({ message: 'Network error' })));

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mockUpdateAccounts).not.toHaveBeenCalled();
    });

    it('should not notify on cancelled task', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      runTaskResult.mockResolvedValue(err(Cancelled({ message: 'cancelled' })));

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators();

      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should pass filter payload to API', async () => {
      mockIsEth2Enabled.mockReturnValue(true);

      runTaskResult.mockImplementation(async (fn: () => Promise<unknown>) => {
        await fn();
        return ok({ entries: [], entriesFound: 0, entriesLimit: 100 });
      });

      const { fetchEthStakingValidators } = useEthValidatorFetching();
      await fetchEthStakingValidators({ ignoreCache: true });

      expect(mockGetEth2Validators).toHaveBeenCalledWith({ ignoreCache: true });
    });
  });
});
