import type { BitcoinAccounts, BlockchainAccount, BlockchainAccountGroupWithBalance } from '@/types/blockchain/accounts';
import type { BlockchainTotals, BtcBalances } from '@/types/blockchain/balances';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { convertBtcAccounts, convertBtcBalances } from '@/utils/blockchain/accounts';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { type Balance, bigNumberify, Blockchain, Zero } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBlockchainAccountData } from './use-blockchain-account-data';
import '@test/i18n';

// Test data factory functions for better maintainability
function createTestBalance(amount: number, usdValue: number): Balance {
  return {
    amount: bigNumberify(amount),
    usdValue: bigNumberify(usdValue),
  };
}

describe('useBlockchainAccountData', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  describe('bitcoin account functionality', () => {
    it('should handle BTC account aggregation correctly', async () => {
      const accounts: BitcoinAccounts = {
        standalone: [{
          address: '123',
          label: null,
          tags: null,
        }],
        xpubs: [{
          addresses: [{
            address: '1234',
            label: null,
            tags: null,
          }],
          derivationPath: 'm',
          label: null,
          tags: null,
          xpub: 'xpub123',
        }, {
          addresses: null,
          derivationPath: null,
          label: '123',
          tags: ['a'],
          xpub: 'xpub1234',
        }],
      };

      const btcBalances: BtcBalances = {
        standalone: {
          123: createTestBalance(10, 10),
        },
        xpubs: [{
          addresses: {
            1234: createTestBalance(10, 10),
          },
          derivationPath: 'm',
          xpub: 'xpub123',
        }],
      };

      const totals: BlockchainTotals = {
        assets: {
          [Blockchain.BTC.toUpperCase()]: {
            address: createTestBalance(20, 20),
          },
        },
        liabilities: {},
      };

      const { fetchAccounts } = useBlockchainAccountData();
      const { updateAccounts } = useBlockchainAccountsStore();
      const { updateBalances } = useBalancesStore();
      const { getBlockchainAccounts } = useBlockchainAccountData();

      // Convert and store BTC accounts and balances
      updateAccounts(
        Blockchain.BTC,
        convertBtcAccounts(chain => get(chain).toUpperCase(), Blockchain.BTC, accounts),
      );
      updateBalances(Blockchain.BTC, convertBtcBalances(Blockchain.BTC, totals, btcBalances));

      // Test getBlockchainAccounts functionality
      expect(getBlockchainAccounts(Blockchain.BTC)).toEqual([{
        amount: bigNumberify(10),
        chain: Blockchain.BTC,
        data: {
          address: '1234',
          type: 'address',
        },
        expansion: undefined,
        groupId: 'xpub123#m#btc',
        label: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
        type: 'account',
        usdValue: bigNumberify(10),
      }, {
        amount: bigNumberify(10),
        chain: Blockchain.BTC,
        data: {
          address: '123',
          type: 'address',
        },
        expansion: undefined,
        groupId: '123',
        label: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
        type: 'account',
        usdValue: bigNumberify(10),
      }]);

      // Test fetchAccounts functionality
      const knownGroups = await fetchAccounts({ limit: 10, offset: 0 });

      const chain = Blockchain.BTC.toString();

      const expectedGroups: BlockchainAccountGroupWithBalance[] = [{
        chains: [chain],
        data: {
          address: '123',
          type: 'address',
        },
        label: '123',
        tags: undefined,
        type: 'group',
        usdValue: bigNumberify(10),
      }, {
        amount: bigNumberify(10),
        chains: [chain],
        data: {
          derivationPath: 'm',
          type: 'xpub',
          xpub: 'xpub123',
        },
        expansion: 'accounts',
        label: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
        type: 'group',
        usdValue: bigNumberify(10),
      }, {
        amount: Zero,
        chains: [chain],
        data: {
          derivationPath: undefined,
          type: 'xpub',
          xpub: 'xpub1234',
        },
        label: '123',
        nativeAsset: 'BTC',
        tags: ['a'],
        type: 'group',
        usdValue: Zero,
      }];

      expect(knownGroups.data).toEqual(expectedGroups);
    });

    it('should return empty array when no BTC accounts exist', () => {
      const { getBlockchainAccounts } = useBlockchainAccountData();
      const result = getBlockchainAccounts(Blockchain.BTC);
      expect(result).toEqual([]);
    });

    it('should handle BTC xpub accounts correctly', () => {
      const { updateAccounts } = useBlockchainAccountsStore();
      const { getBlockchainAccounts } = useBlockchainAccountData();

      const accounts: BitcoinAccounts = {
        standalone: [],
        xpubs: [{
          addresses: [{
            address: 'xpub-derived-addr-1',
            label: null,
            tags: null,
          }],
          derivationPath: 'm/0',
          label: 'Test xpub',
          tags: ['xpub-tag'],
          xpub: 'xpub123456',
        }],
      };

      updateAccounts(
        Blockchain.BTC,
        convertBtcAccounts(chain => get(chain).toUpperCase(), Blockchain.BTC, accounts),
      );

      const result = getBlockchainAccounts(Blockchain.BTC);

      // Should contain the derived address, not the xpub itself
      expect(result).toHaveLength(1);
      const firstElement = result[0];
      expect(getAccountAddress(firstElement)).toBe('xpub-derived-addr-1');
      expect(firstElement.groupId).toBe('xpub123456#m/0#btc');
    });

    it('should filter out xpub accounts from getBlockchainAccounts', () => {
      const { updateAccounts } = useBlockchainAccountsStore();
      const { getBlockchainAccounts } = useBlockchainAccountData();

      // Manually create accounts with xpub type to test filtering
      const mockAccounts: BlockchainAccount[] = [{
        chain: Blockchain.BTC,
        data: { type: 'xpub', xpub: 'xpub123' },
        groupHeader: false,
        groupId: undefined,
        nativeAsset: 'BTC',
        tags: undefined,
      }];

      updateAccounts(Blockchain.BTC, mockAccounts);

      const result = getBlockchainAccounts(Blockchain.BTC);

      // Should filter out xpub accounts
      expect(result).toEqual([]);
    });
  });

  describe('general account functionality', () => {
    it('should return account details for valid chain and address', () => {
      const { getAccountDetails } = useBlockchainAccountData();
      const { balances } = storeToRefs(useBalancesStore());

      // Setup test balance data directly in the store
      set(balances, {
        [Blockchain.ETH]: {
          '0x123': {
            assets: {
              ETH: {
                protocol1: createTestBalance(10, 30000),
              },
            },
            liabilities: {},
          },
        },
      });

      const result = getAccountDetails(Blockchain.ETH, '0x123');

      expect(result.assets).toHaveLength(1);
      expect(result.assets[0].asset).toBe('ETH');
      expect(result.assets[0].amount).toEqual(bigNumberify(10));
      expect(result.assets[0].usdValue).toEqual(bigNumberify(30000));
      expect(result.liabilities).toEqual([]);
    });

    it('should return empty details for non-existent account', () => {
      const { getAccountDetails } = useBlockchainAccountData();

      const result = getAccountDetails(Blockchain.ETH, '0x999');

      expect(result).toEqual({
        assets: [],
        liabilities: [],
      });
    });

    it('should handle account tags correctly', () => {
      const { useAccountTags } = useBlockchainAccountData();
      const { updateAccounts } = useBlockchainAccountsStore();

      const mockAccounts: BlockchainAccount[] = [{
        chain: Blockchain.ETH,
        data: { address: '0x123', type: 'address' },
        groupHeader: false,
        groupId: undefined,
        nativeAsset: 'ETH',
        tags: ['tag1', 'tag2'],
      }];

      updateAccounts(Blockchain.ETH, mockAccounts);

      const tags = get(useAccountTags('0x123'));

      expect(tags).toEqual(['tag1', 'tag2']);
    });

    it('should return empty tags for account without tags', () => {
      const { useAccountTags } = useBlockchainAccountData();

      const tags = get(useAccountTags('0x999'));

      expect(tags).toEqual([]);
    });
  });
});
