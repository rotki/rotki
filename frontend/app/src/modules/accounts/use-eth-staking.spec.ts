import type { BlockchainAccount, ValidatorData } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { runSpecWith } from '@test/utils/mocks/native-task';
import { createPinia, setActivePinia } from 'pinia';
import { err, ok, type Result } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { Module } from '@/modules/core/common/modules';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import '@test/i18n';

const h = vi.hoisted(() => {
  const activeModules: string[] = [];
  const runTask = vi.fn();
  return {
    addEth2Validator: vi.fn(),
    deleteEth2Validators: vi.fn(),
    editEth2Validator: vi.fn(),
    fetchEthStakingValidators: vi.fn(),
    runTask,
    showErrorMessage: vi.fn(),
    submitTask: vi.fn(),
    // plain holder: the SUT only reads these, so the mocks expose them via computed()
    state: { activeModules, premium: false },
  };
});

h.submitTask.mockImplementation(runSpecWith(h.runTask));

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    addEth2Validator: h.addEth2Validator,
    deleteEth2Validators: h.deleteEth2Validators,
    editEth2Validator: h.editEth2Validator,
  })),
}));

vi.mock('@/modules/staking/eth/use-eth-validator-fetching', () => ({
  useEthValidatorFetching: vi.fn(() => ({ fetchEthStakingValidators: h.fetchEthStakingValidators })),
}));

vi.mock('@/modules/premium/use-premium', async () => {
  const { computed } = await import('vue');
  return { usePremium: vi.fn(() => computed(() => h.state.premium)) };
});

vi.mock('@/modules/settings/use-setting', async () => {
  const { computed } = await import('vue');
  return { useSetting: vi.fn(() => computed(() => h.state.activeModules)) };
});

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
  useNotifications: vi.fn(() => ({ showErrorMessage: h.showErrorMessage })),
}));

vi.mock('@/modules/task-center/use-native-task', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/task-center/use-native-task')>();
  return {
    ...actual,
    useNativeTask: vi.fn(() => ({
      statusOf: vi.fn(),
      submitTask: h.submitTask,
    })),
  };
});

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

/**
 * Drives the add producer's native `run`: `runTaskResult` invokes the api call (unless the outcome
 * is a pre-run failure) and yields a plainfp {@link Result} the orchestrator contract expects.
 */
function whenAdd(outcome: Result<boolean, TaskError>, invoke = true): void {
  h.runTask.mockImplementation(async (task: () => Promise<unknown>): Promise<Result<boolean, TaskError>> => {
    if (invoke)
      await task();
    return outcome;
  });
}

function validatorAccount(publicKey: string, index: number): BlockchainAccount<ValidatorData> {
  return { chain: 'eth2', data: { index, publicKey, status: 'active', type: 'validator' }, nativeAsset: 'ETH2' };
}

async function importModule(): Promise<typeof import('./use-eth-staking')> {
  return import('./use-eth-staking');
}

describe('useEthStaking', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    h.state.activeModules = [Module.ETH2];
    h.state.premium = false;
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('addEth2Validator', () => {
    const payload = { publicKey: '0xpub', validatorIndex: '1' };

    it('should return failure without running a task when eth2 is disabled', async () => {
      h.state.activeModules = [];
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(result).toStrictEqual({ message: '', success: false });
      expect(h.submitTask).not.toHaveBeenCalled();
    });

    it('should return success when the validator is added', async () => {
      whenAdd(ok(true));
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(h.addEth2Validator).toHaveBeenCalledWith(payload);
      expect(result).toStrictEqual({ message: '', success: true });
    });

    it('should report failure when the backend reports the validator was not added', async () => {
      whenAdd(ok(false));
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(result).toStrictEqual({ message: '', success: false });
    });

    it('should surface validation errors from an actionable failure', async () => {
      whenAdd(err(TaskFailed({ cause: new ApiValidationError('{"publicKey":["Invalid key"]}'), message: 'bad' })), false);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      assert(!result.success);
      expect(result.message).not.toBe('');
    });

    it('should return the failure message for a plain actionable failure', async () => {
      whenAdd(err(TaskFailed({ message: 'some error' })), false);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(result).toStrictEqual({ message: 'some error', success: false });
    });

    it('should return a generic failure on a cancelled task', async () => {
      whenAdd(err(Cancelled({ message: 'cancelled' })), false);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(result).toStrictEqual({ message: '', success: false });
    });
  });

  describe('editEth2Validator', () => {
    const payload = { publicKey: '0xpub', validatorIndex: '1' };

    it('should return failure without calling the api when eth2 is disabled', async () => {
      h.state.activeModules = [];
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().editEth2Validator(payload);
      expect(result).toStrictEqual({ message: '', success: false });
      expect(h.editEth2Validator).not.toHaveBeenCalled();
    });

    it('should return success when the edit succeeds', async () => {
      h.editEth2Validator.mockResolvedValue(true);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().editEth2Validator(payload);
      expect(h.editEth2Validator).toHaveBeenCalledWith(payload);
      expect(result).toStrictEqual({ message: '', success: true });
    });

    it('should map a validation error into the message', async () => {
      h.editEth2Validator.mockRejectedValue(new ApiValidationError('{"publicKey":["Invalid key"]}'));
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().editEth2Validator(payload);
      assert(!result.success);
      expect(result.message).not.toBe('');
    });

    it('should return the error message on a generic failure', async () => {
      h.editEth2Validator.mockRejectedValue(new Error('boom'));
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().editEth2Validator(payload);
      expect(result).toStrictEqual({ message: 'boom', success: false });
    });
  });

  describe('deleteEth2Validators', () => {
    beforeEach(() => {
      const accountsStore = useBlockchainAccountsStore();
      accountsStore.updateAccounts(Blockchain.ETH2, [
        validatorAccount('0xaaa', 1),
        validatorAccount('0xbbb', 2),
      ]);
    });

    it('should refetch validators on success for a non-premium user', async () => {
      h.deleteEth2Validators.mockResolvedValue(true);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().deleteEth2Validators(['0xaaa']);
      expect(result).toBe(true);
      expect(h.deleteEth2Validators).toHaveBeenCalledWith([
        expect.objectContaining({ publicKey: '0xaaa' }),
      ]);
      expect(h.fetchEthStakingValidators).toHaveBeenCalledOnce();
    });

    it('should locally prune the accounts on success for a premium user', async () => {
      h.state.premium = true;
      h.deleteEth2Validators.mockResolvedValue(true);
      const { useEthStaking } = await importModule();
      await useEthStaking().deleteEth2Validators(['0xaaa']);
      const accountsStore = useBlockchainAccountsStore();
      const remaining = accountsStore.getAccounts(Blockchain.ETH2).map(a => 'publicKey' in a.data ? a.data.publicKey : '');
      expect(remaining).toEqual(['0xbbb']);
      expect(h.fetchEthStakingValidators).not.toHaveBeenCalled();
    });

    it('should not mutate state when the api reports no removal', async () => {
      h.deleteEth2Validators.mockResolvedValue(false);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().deleteEth2Validators(['0xaaa']);
      expect(result).toBe(false);
      expect(h.fetchEthStakingValidators).not.toHaveBeenCalled();
    });

    it('should show an error message when deletion fails', async () => {
      h.deleteEth2Validators.mockRejectedValue(new Error('delete failed'));
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().deleteEth2Validators(['0xaaa']);
      expect(result).toBe(false);
      expect(h.showErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('validatorsLimitInfo', () => {
    it('should report zeros when no limits are known', async () => {
      const { useEthStaking } = await importModule();
      expect(get(useEthStaking().validatorsLimitInfo)).toStrictEqual({ limit: 0, showWarning: false, total: 0 });
    });

    it('should warn when the limit is reached', async () => {
      const { useBlockchainValidatorsStore } = await import('@/modules/staking/use-blockchain-validators-store');
      const { stakingValidatorsLimits } = storeToRefs(useBlockchainValidatorsStore());
      set(stakingValidatorsLimits, { limit: 5, total: 5 });
      const { useEthStaking } = await importModule();
      expect(get(useEthStaking().validatorsLimitInfo)).toStrictEqual({ limit: 5, showWarning: true, total: 5 });
    });

    it('should not warn when below the limit', async () => {
      const { useBlockchainValidatorsStore } = await import('@/modules/staking/use-blockchain-validators-store');
      const { stakingValidatorsLimits } = storeToRefs(useBlockchainValidatorsStore());
      set(stakingValidatorsLimits, { limit: 10, total: 3 });
      const { useEthStaking } = await importModule();
      expect(get(useEthStaking().validatorsLimitInfo)).toStrictEqual({ limit: 10, showWarning: false, total: 3 });
    });
  });

  describe('passthrough exports', () => {
    it('should expose the store ownership updater and validator fetcher', async () => {
      const { useEthStaking } = await importModule();
      const staking = useEthStaking();
      expect(staking.fetchEthStakingValidators).toBe(h.fetchEthStakingValidators);
      expect(typeof staking.updateEthStakingOwnership).toBe('function');
    });
  });
});
