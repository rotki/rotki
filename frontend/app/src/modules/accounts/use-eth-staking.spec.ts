import type { BlockchainAccount, ValidatorData } from '@/modules/accounts/blockchain-accounts';
import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { Blockchain } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { Module } from '@/modules/core/common/modules';
import '@test/i18n';

const h = vi.hoisted(() => ({
  addEth2Validator: vi.fn(),
  deleteEth2Validators: vi.fn(),
  editEth2Validator: vi.fn(),
  fetchEthStakingValidators: vi.fn(),
  resetStatus: vi.fn(),
  runTask: vi.fn(),
  showErrorMessage: vi.fn(),
  // plain holder: the SUT only reads these, so the mocks expose them via computed()
  state: { activeModules: [] as string[], premium: false },
}));

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

vi.mock('@/modules/shell/sync-progress/use-status-updater', () => ({
  useStatusUpdater: vi.fn(() => ({ resetStatus: h.resetStatus })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (e: unknown): string => (e instanceof Error ? e.message : String(e)),
  useNotifications: vi.fn(() => ({ showErrorMessage: h.showErrorMessage })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/modules/core/tasks/use-task-handler')>();
  return { ...actual, useTaskHandler: vi.fn(() => ({ runTask: h.runTask })) };
});

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn() },
}));

function success<R>(result: R): TaskResult<R> {
  return { result, success: true };
}

function actionable(message: string, error: unknown = new Error(message)): TaskResult<never> {
  return { backendCancelled: false, cancelled: false, error, message, skipped: false, success: false };
}

function cancelled(): TaskResult<never> {
  return { backendCancelled: false, cancelled: true, message: 'cancelled', skipped: false, success: false };
}

function whenTask<R>(outcome: TaskResult<R>, invoke = true): void {
  h.runTask.mockImplementation(async (task: () => Promise<unknown>): Promise<TaskResult<R>> => {
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
      expect(h.runTask).not.toHaveBeenCalled();
    });

    it('should reset statuses and return success when the validator is added', async () => {
      whenTask(success(true));
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(h.addEth2Validator).toHaveBeenCalledWith(payload);
      expect(result).toStrictEqual({ message: '', success: true });
      expect(h.resetStatus).toHaveBeenCalledTimes(3);
    });

    it('should not reset statuses when the result is falsy', async () => {
      whenTask(success(false));
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(result).toStrictEqual({ message: '', success: false });
      expect(h.resetStatus).not.toHaveBeenCalled();
    });

    it('should surface validation errors from an actionable failure', async () => {
      whenTask(actionable('bad', new ApiValidationError('{"publicKey":["Invalid key"]}')), false);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      assert(!result.success);
      expect(result.message).not.toBe('');
    });

    it('should return the failure message for a plain actionable failure', async () => {
      whenTask(actionable('some error'), false);
      const { useEthStaking } = await importModule();
      const result = await useEthStaking().addEth2Validator(payload);
      expect(result).toStrictEqual({ message: 'some error', success: false });
    });

    it('should return a generic failure on a cancelled task', async () => {
      whenTask(cancelled(), false);
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
