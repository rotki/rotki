import type { EffectScope } from 'vue';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify, Zero } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useEthValidatorManagement } from '@/modules/staking/eth/use-eth-validator-management';

const mockQueryEth2Validators = vi.fn();
const mockEthStakingValidators = ref<EthereumValidator[]>([]);

vi.mock('@/modules/accounts/api/use-blockchain-accounts-api', () => ({
  useBlockchainAccountsApi: vi.fn(() => ({
    queryEth2Validators: mockQueryEth2Validators,
  })),
}));

vi.mock('@/modules/staking/use-blockchain-validators-store', () => ({
  useBlockchainValidatorsStore: vi.fn(() => ({
    ethStakingValidators: mockEthStakingValidators,
  })),
}));

const EXITED_VALIDATOR_AMOUNT = 0;

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

    it('should total zero when every selected validator has exited', () => {
      set(mockEthStakingValidators, [validator('0xaaa', 32), validator('0xexited', EXITED_VALIDATOR_AMOUNT)]);

      const { setTotal, total } = create();
      setTotal([{ index: 1000, publicKey: '0xexited', status: 'exited' }]);

      expect(get(total)).toStrictEqual(Zero);
    });

    it('should sum only the backed part of a mixed selection', () => {
      set(mockEthStakingValidators, [validator('0xactive', 32), validator('0xexited', EXITED_VALIDATOR_AMOUNT)]);

      const { setTotal, total } = create();
      setTotal([
        { index: 9, publicKey: '0xactive', status: 'active' },
        { index: 1000, publicKey: '0xexited', status: 'exited' },
      ]);

      expect(get(total).toNumber()).toBe(32);
    });
  });

  describe('fetchValidatorsWithFilter', () => {
    function answer(entries: Array<{ index: number; publicKey: string; status: string }>): unknown {
      return { entries, entriesFound: entries.length, entriesLimit: 100 };
    }

    function deferAnswerResolversInRequestOrder(): Array<(value: unknown) => void> {
      const resolvers: Array<(value: unknown) => void> = [];
      mockQueryEth2Validators.mockImplementation(async () => new Promise((resolve) => {
        resolvers.push(resolve);
      }));
      return resolvers;
    }

    it('should skip the request and total all validators when the filter is empty', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 2), validator('0xbbb', 3)]);

      const { fetchValidatorsWithFilter, total } = create();
      await fetchValidatorsWithFilter();

      expect(mockQueryEth2Validators).not.toHaveBeenCalled();
      expect(get(total).toNumber()).toBe(5);
    });

    it('should query by validator indices when validators are selected', async () => {
      mockQueryEth2Validators.mockResolvedValue(answer([]));

      const { modelSelection } = create();
      set(modelSelection, { validators: [{ index: 42, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();

      expect(mockQueryEth2Validators).toHaveBeenCalledWith({ validatorIndices: [42] });
    });

    it('should query by addresses when accounts are selected', async () => {
      mockQueryEth2Validators.mockResolvedValue(answer([]));

      const { modelSelection } = create();
      set(modelSelection, { accounts: [{ address: '0xdead', chain: 'eth2' }] });
      await flushPromises();

      expect(mockQueryEth2Validators).toHaveBeenCalledWith({ addresses: ['0xdead'] });
    });

    it('should merge the status filter with the account selection', async () => {
      mockQueryEth2Validators.mockResolvedValue(answer([]));

      const { modelFilter, modelSelection } = create();
      set(modelSelection, { validators: [{ index: 7, publicKey: '0xaaa', status: 'active' }] });
      set(modelFilter, { fromTimestamp: 100, status: 'active', toTimestamp: 200 });
      await flushPromises();

      expect(mockQueryEth2Validators).toHaveBeenLastCalledWith({ status: 'active', validatorIndices: [7] });
    });

    it('should update the total from the result on success', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      mockQueryEth2Validators.mockResolvedValue(answer([{ index: 1, publicKey: '0xbbb', status: 'active' }]));

      const { modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xbbb', status: 'active' }] });
      await flushPromises();

      expect(get(total).toNumber()).toBe(6);
    });

    it('should swallow a failed request rather than let it reject the watcher', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4)]);
      mockQueryEth2Validators.mockRejectedValue(new Error('boom'));

      const { modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();

      expect(get(total)).toStrictEqual(Zero);
    });

    it('should recover on the next successful recompute after a failure', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      mockQueryEth2Validators.mockRejectedValue(new Error('boom'));

      const { modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();

      mockQueryEth2Validators.mockResolvedValue(answer([{ index: 2, publicKey: '0xbbb', status: 'active' }]));
      set(modelSelection, { validators: [{ index: 2, publicKey: '0xbbb', status: 'active' }] });
      await flushPromises();

      expect(get(total).toNumber()).toBe(6);
    });

    it('should ignore a response the newest filter has already superseded', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      const resolvers = deferAnswerResolversInRequestOrder();

      const { modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();
      set(modelSelection, { validators: [{ index: 2, publicKey: '0xbbb', status: 'active' }] });
      await flushPromises();

      expect(resolvers).toHaveLength(2);

      const [resolveOlderRequest, resolveNewerRequest] = resolvers;
      resolveNewerRequest(answer([{ index: 2, publicKey: '0xbbb', status: 'active' }]));
      await flushPromises();
      resolveOlderRequest(answer([{ index: 1, publicKey: '0xaaa', status: 'active' }]));
      await flushPromises();

      expect(get(total).toNumber()).toBe(6);
    });

    it('should still apply the answer when the same filter is requested twice, since both answers are valid', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      const resolvers = deferAnswerResolversInRequestOrder();

      const { modelFilter, modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 2, publicKey: '0xbbb', status: 'active' }] });
      await flushPromises();

      set(modelFilter, {});
      await flushPromises();

      resolvers[0](answer([{ index: 2, publicKey: '0xbbb', status: 'active' }]));
      await flushPromises();

      expect(get(total).toNumber()).toBe(6);
    });

    it('should ignore an in-flight response once the total is set directly', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      const resolvers = deferAnswerResolversInRequestOrder();

      const { modelSelection, setTotal, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();

      setTotal();
      resolvers[0](answer([{ index: 1, publicKey: '0xaaa', status: 'active' }]));
      await flushPromises();

      expect(get(total).toNumber()).toBe(10);
    });
  });
});
