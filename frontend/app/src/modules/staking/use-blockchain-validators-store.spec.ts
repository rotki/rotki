import type { ValidatorDetails } from '@/modules/accounts/blockchain-accounts';
import { type Balance, Blockchain, Zero } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainValidatorsStore } from './use-blockchain-validators-store';

describe('useBlockchainValidatorsStore', () => {
  let store: ReturnType<typeof useBlockchainValidatorsStore>;
  let accountsStore: ReturnType<typeof useBlockchainAccountsStore>;
  let balancesStore: ReturnType<typeof useBalancesStore>;

  const mockValidatorData1: ValidatorDetails = {
    index: 1,
    ownershipPercentage: '100',
    publicKey: '0x1234567890abcdef',
    status: 'active',
  };

  const mockValidatorData2: ValidatorDetails = {
    index: 2,
    ownershipPercentage: '100',
    publicKey: '0xabcdef1234567890',
    status: 'active',
  };

  const mockBalance: Balance = {
    amount: Zero,
    value: Zero,
  };

  beforeEach(() => {
    setActivePinia(createPinia());

    accountsStore = useBlockchainAccountsStore();
    balancesStore = useBalancesStore();
    store = useBlockchainValidatorsStore();
  });

  describe('ethStakingValidators', () => {
    it('should return empty array when no ETH2 accounts exist', () => {
      const validators = get(store.ethStakingValidators);
      expect(validators).toEqual([]);
    });

    it('should compute validators with and without balances', () => {
      accountsStore.accounts[Blockchain.ETH2] = [{
        ...mockValidatorData1,
        chain: Blockchain.ETH2,
        kind: 'validator',
        label: 'Test Validator 1',
      }, {
        ...mockValidatorData2,
        chain: Blockchain.ETH2,
        kind: 'validator',
        label: 'Test Validator 2',
      }];

      balancesStore.balances[Blockchain.ETH2] = {
        [mockValidatorData1.publicKey]: {
          assets: {
            ETH2: {
              address: mockBalance,
            },
          },
          liabilities: {},
        },
      };

      const validators = get(store.ethStakingValidators);
      expect(validators).toHaveLength(2);

      expect(validators[0], 'maps to proper balance').toEqual({
        ...mockValidatorData1,
        ...mockBalance,
      });

      expect(validators[1], 'maps to zero balance').toEqual({
        ...mockValidatorData2,
        amount: Zero,
        value: Zero,
      });
    });
  });
});
