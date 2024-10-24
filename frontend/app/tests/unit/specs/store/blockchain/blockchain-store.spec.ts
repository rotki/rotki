import { beforeEach, describe, expect, it } from 'vitest';
import { Blockchain } from '@rotki/common';
import { useBlockchainStore } from '@/store/blockchain';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { AssetPrices } from '@/types/prices';
import type { Balance } from '@/types/blockchain/balances';

describe('useBlockchainStore', () => {
  let store: ReturnType<typeof useBlockchainStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useBlockchainStore();
  });

  describe('updatePrices', () => {
    it('default', () => {
      const assetPrices: AssetPrices = {
        ETH: {
          value: bigNumberify(2500),
          isManualPrice: false,
        },
      };

      store.updateBalances(Blockchain.ETH, {
        perAccount: {
          [Blockchain.ETH]: {
            '0xacc': {
              assets: {
                ETH: {
                  amount: bigNumberify(10),
                  value: bigNumberify(20000),
                },
              },
              liabilities: {},
            },
          },
        },
        totals: {
          assets: {
            ETH: {
              amount: bigNumberify(10),
              value: bigNumberify(20000),
            },
          },
          liabilities: {},
        },
      });

      store.updatePrices(assetPrices);

      expect(store.aggregatedTotals.ETH).toEqual({
        amount: bigNumberify(10),
        value: bigNumberify(25000),
      } satisfies Balance);

      expect(store.balances.eth['0xacc'].assets.ETH).toEqual({
        amount: bigNumberify(10),
        value: bigNumberify(25000),
      } satisfies Balance);
    });
  });

  it('removeAccounts', () => {
    const account: BlockchainAccount<AddressData> = {
      data: {
        type: 'address',
        address: '0x123',
      },
      chain: 'eth',
      nativeAsset: 'ETH',
    };
    const balances = {
      '0x123': {
        assets: {
          ETH: {
            amount: bigNumberify(1),
            value: bigNumberify(2501),
          },
        },
        liabilities: {},
      },
    };
    store.updateAccounts('eth', [account]);
    store.updateBalances('eth', {
      perAccount: {
        eth: balances,
      },
      totals: {
        assets: {
          ETH: {
            amount: bigNumberify(1),
            value: bigNumberify(2501),
          },
        },
        liabilities: {},
      },
    });
    expect(store.accounts).toMatchObject({ eth: [account] });
    expect(store.balances).toMatchObject({ eth: balances });
    store.removeAccounts({ addresses: ['0x123'], chains: ['eth'] });
    expect(store.accounts).toMatchObject({ eth: [] });
    expect(store.balances).toMatchObject({ eth: {} });
  });
});
