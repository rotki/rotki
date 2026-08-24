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
      // The balance response omits exited validators entirely, so they carry a stand-in zero.
      set(mockEthStakingValidators, [validator('0xaaa', 32), validator('0xexited', 0)]);

      const { setTotal, total } = create();
      setTotal([{ index: 1000, publicKey: '0xexited', status: 'exited' }]);

      expect(get(total)).toStrictEqual(Zero);
    });

    it('should sum only the backed part of a mixed selection', () => {
      set(mockEthStakingValidators, [validator('0xactive', 32), validator('0xexited', 0)]);

      const { setTotal, total } = create();
      setTotal([
        { index: 9, publicKey: '0xactive', status: 'active' },
        { index: 1000, publicKey: '0xexited', status: 'exited' },
      ]);

      expect(get(total).toNumber()).toBe(32);
    });
  });

  describe('fetchValidatorsWithFilter', () => {
    /** The shape `queryEth2Validators` resolves with, for the given entries. */
    function answer(entries: Array<{ index: number; publicKey: string; status: string }>): unknown {
      return { entries, entriesFound: entries.length, entriesLimit: 100 };
    }

    /**
     * Holds every request open so a test can decide the order the answers arrive in.
     * @returns the resolvers, in request order.
     */
    function deferAnswers(): Array<(value: unknown) => void> {
      const pending: Array<(value: unknown) => void> = [];
      mockQueryEth2Validators.mockImplementation(async () => new Promise((resolve) => {
        pending.push(resolve);
      }));
      return pending;
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
      const pending = deferAnswers();

      const { modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();
      set(modelSelection, { validators: [{ index: 2, publicKey: '0xbbb', status: 'active' }] });
      await flushPromises();

      expect(pending).toHaveLength(2);

      // The newer filter answers first, then the older request arrives late. Nothing serialises
      // these, so the late one must be dropped rather than allowed to overwrite the newer answer.
      pending[1](answer([{ index: 2, publicKey: '0xbbb', status: 'active' }]));
      await flushPromises();
      pending[0](answer([{ index: 1, publicKey: '0xaaa', status: 'active' }]));
      await flushPromises();

      expect(get(total).toNumber()).toBe(6);
    });

    it('should still apply the answer when the same filter is requested twice', async () => {
      // The premium component re-emits `update:filter` after every change, so an unchanged filter
      // is re-requested as a matter of course. Both requests carry the same filter, so both answers
      // are valid: a guard keyed to the call rather than to the filter rejects the first one's
      // answer and `total` then never updates at all.
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      const pending = deferAnswers();

      const { modelFilter, modelSelection, total } = create();
      set(modelSelection, { validators: [{ index: 2, publicKey: '0xbbb', status: 'active' }] });
      await flushPromises();

      // A distinct object carrying nothing new, which is what the re-emit produces.
      set(modelFilter, {});
      await flushPromises();

      pending[0](answer([{ index: 2, publicKey: '0xbbb', status: 'active' }]));
      await flushPromises();

      expect(get(total).toNumber()).toBe(6);
    });

    it('should ignore an in-flight response once the total is set directly', async () => {
      set(mockEthStakingValidators, [validator('0xaaa', 4), validator('0xbbb', 6)]);
      const pending = deferAnswers();

      const { modelSelection, setTotal, total } = create();
      set(modelSelection, { validators: [{ index: 1, publicKey: '0xaaa', status: 'active' }] });
      await flushPromises();

      // What the page refresh does: recompute over everything while a filtered request is open.
      setTotal();
      pending[0](answer([{ index: 1, publicKey: '0xaaa', status: 'active' }]));
      await flushPromises();

      expect(get(total).toNumber()).toBe(10);
    });
  });
});
