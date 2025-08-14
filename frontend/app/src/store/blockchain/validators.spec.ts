import type { ValidatorData } from '@/types/blockchain/accounts';
import { type Balance, Blockchain, Zero } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainValidatorsStore } from './validators';

describe('useBlockchainValidatorsStore', () => {
  let store: ReturnType<typeof useBlockchainValidatorsStore>;
  let accountsStore: ReturnType<typeof useBlockchainAccountsStore>;
  let balancesStore: ReturnType<typeof useBalancesStore>;

  const mockValidatorData1: ValidatorData = {
    index: 1,
    ownershipPercentage: '100',
    publicKey: '0x1234567890abcdef',
    status: 'active',
    type: 'validator',
  };

  const mockValidatorData2: ValidatorData = {
    index: 2,
    ownershipPercentage: '100',
    publicKey: '0xabcdef1234567890',
    status: 'active',
    type: 'validator',
  };

  const mockBalance: Balance = {
    amount: Zero,
    usdValue: Zero,
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
        chain: Blockchain.ETH2,
        data: mockValidatorData1,
        label: 'Test Validator 1',
        nativeAsset: 'ETH2',
      }, {
        chain: Blockchain.ETH2,
        data: mockValidatorData2,
        label: 'Test Validator 2',
        nativeAsset: 'ETH2',
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
        usdValue: Zero,
      });
    });
  });
});
