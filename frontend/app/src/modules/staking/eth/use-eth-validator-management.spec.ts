import type { EffectScope } from 'vue';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify, Zero } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useEthValidatorManagement } from '@/modules/staking/eth/use-eth-validator-management';

const mockGetEth2Validators = vi.fn();
const mockRunTask = vi.fn();
const mockEthStakingValidators = ref<EthereumValidator[]>([]);

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    getEth2Validators: mockGetEth2Validators,
  })),
}));

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: vi.fn(() => ({
    runTask: mockRunTask,
  })),
}));

vi.mock('@/modules/staking/use-blockchain-validators-store', () => ({
  useBlockchainValidatorsStore: vi.fn(() => ({
    ethStakingValidators: mockEthStakingValidators,
  })),
}));

function validator(publicKey: string, amount: number): EthereumValidator {
  return createMock<EthereumValidator>({ amount: bigNumberify(amount), publicKey });
}

describe('useEthValidatorManagement', () => {
  let scope: EffectScope;

  function create(): ReturnType<typeof useEthValidatorManagement> {
    return scope.run(() => useEthValidatorManagement())!;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    scope = effectScope();
    set(mockEthStakingValidators, []);
  });

  afterEach(() => {
    scope.stop();
  });

  describe('setTotal', () => {
    it('should sum all staking validators when no filter is given', () => {
      set(mockEthStakingValidators, [validator('0xaaa', 2), validator('0xbbb', 3)]);

      const { setTotal, total } = create();
      setTotal();

      expect(get(total).toNumber()).toBe(5);
    });

    it('should only sum validators matching the provided public keys', () => {
      set(mockEthStakingValidators, [validator('0xaaa', 2), validator('0xbbb', 3)]);

      const { setTotal, total } = create();
      setTotal([{ index: 1, publicKey: '0xbbb', status: 'active' }]);

      expect(get(total).toNumber()).toBe(3);
    });

    it('should be zero when no validators match', () => {
      set(mockEthStakingValidators, [validator('0xaaa', 2)]);

      const { setTotal, total } = create();
      setTotal([{ index: 9, publicKey: '0xzzz', status: 'active' }]);

      expect(get(total)).toStrictEqual(Zero);
    });
  });

  describe('fetchValidatorsWithFilter', () => {
    it('should skip the task and total all validators when the filter is empty', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 2), validator('0xbbb', 3)]);

      const { fetchValidatorsWithFilter, total } = create();
      await fetchValidatorsWithFilter();

      expect(mockRunTask).not.toHaveBeenCalled();
      expect(get(total).toNumber()).toBe(5);
    });

    it('should query by validator indices when validators are selected', async () => {
      mockRunTask.mockImplementation(async (fn: () => Promise<unknown>) => {
        await fn();
        return { result: { entries: [], entriesFound: 0, entriesLimit: 100 }, success: true };
      });

      const { modelSelection } = create();
      set(modelSelection, { validators: [{ index: 42, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();

      expect(mockRunTask).toHaveBeenCalledOnce();
      expect(mockGetEth2Validators).toHaveBeenCalledWith({ validatorIndices: [42] });
    });

    it('should query by addresses when accounts are selected', async () => {
      mockRunTask.mockImplementation(async (fn: () => Promise<unknown>) => {
        await fn();
        return { result: { entries: [], entriesFound: 0, entriesLimit: 100 }, success: true };
      });

      const { modelSelection } = create();
      set(modelSelection, { accounts: [{ address: '0xdead', chain: 'eth2' }] });
      await flushPromises();

      expect(mockGetEth2Validators).toHaveBeenCalledWith({ addresses: ['0xdead'] });
    });

    it('should merge the status filter with the account selection', async () => {
      mockRunTask.mockImplementation(async (fn: () => Promise<unknown>) => {
        await fn();
        return { result: { entries: [], entriesFound: 0, entriesLimit: 100 }, success: true };
      });

      const { modelFilter, modelSelection } = create();
      set(modelSelection, { validators: [{ index: 7, publicKey: '0xaaa', status: 'active' }] });
      set(modelFilter, { fromTimestamp: 100, status: 'active', toTimestamp: 200 });
      await flushPromises();

      expect(mockGetEth2Validators).toHaveBeenLastCalledWith({ status: 'active', validatorIndices: [7] });
    });

    it('should update the total from the parsed result on success', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      mockRunTask.mockResolvedValue({
        result: { entries: [{ index: 1, publicKey: '0xbbb', status: 'active' }], entriesFound: 1, entriesLimit: 100 },
        success: true,
      });

      const { modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xbbb', status: 'active' }] });
      await flushPromises();

      expect(get(total).toNumber()).toBe(6);
    });

    it('should leave the total unchanged when the task fails', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4)]);
      mockRunTask.mockResolvedValue({
        cancelled: false,
        message: 'boom',
        skipped: false,
        success: false,
      });

      const { modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();

      expect(get(total)).toStrictEqual(Zero);
    });
  });
});
