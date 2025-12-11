import type { AssetPrices } from '@/types/prices';
import { bigNumberify, Blockchain } from '@rotki/common';
import { cloneDeep } from 'es-toolkit';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBalancePricesStore } from '@/store/balances/prices';

describe('useBalancesStore', () => {
  let store: ReturnType<typeof useBalancesStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useBalancesStore();
  });

  it('should update the balance prices and value', () => {
    const { updateBalances, updatePrices } = store;
    const assetPrices: AssetPrices = {
      ETH: {
        isManualPrice: false,
        oracle: 'coingecko',
        usdPrice: null,
        value: bigNumberify(2500),
      },
    };

    // Set up prices in store so getAssetPriceInCurrentCurrency can find the price
    const { prices } = storeToRefs(useBalancePricesStore());
    set(prices, assetPrices);

    updateBalances(Blockchain.ETH, {
      perAccount: {
        [Blockchain.ETH]: {
          '0xacc': {
            assets: {
              ETH: {
                address: {
                  amount: bigNumberify(10),
                  value: bigNumberify(20000),
                },
              },
            },
            liabilities: {},
          },
        },
      },
      totals: {
        assets: {
          ETH: {
            address: {
              amount: bigNumberify(10),
              value: bigNumberify(20000),
            },
          },
        },
        liabilities: {},
      },
    });

    updatePrices(assetPrices);

    expect(store.balances.eth['0xacc'].assets.ETH.address).toMatchObject({
      amount: bigNumberify(10),
      value: bigNumberify(25000),
    });
  });

  describe('removeIgnoredAssets', () => {
    beforeEach(() => {
      store.balances = {
        btc: {
          bc1q: {
            assets: {
              BTC: {
                address: {
                  amount: bigNumberify(1),
                  value: bigNumberify(50000),
                },
              },
            },
            liabilities: {},
          },
        },
        eth: {
          '0xacc1': {
            assets: {
              DAI: {
                address: {
                  amount: bigNumberify(100),
                  value: bigNumberify(100),
                },
              },
              ETH: {
                address: {
                  amount: bigNumberify(10),
                  value: bigNumberify(25000),
                },
              },
              USDC: {
                address: {
                  amount: bigNumberify(200),
                  value: bigNumberify(200),
                },
              },
            },
            liabilities: {
              DAI: {
                address: {
                  amount: bigNumberify(50),
                  value: bigNumberify(50),
                },
              },
            },
          },
          '0xacc2': {
            assets: {
              ETH: {
                address: {
                  amount: bigNumberify(5),
                  value: bigNumberify(12500),
                },
              },
              USDT: {
                address: {
                  amount: bigNumberify(300),
                  value: bigNumberify(300),
                },
              },
            },
            liabilities: {},
          },
        },
      };
    });

    it('should remove specified assets from all accounts', () => {
      expect(store.balances.eth['0xacc1'].assets).toHaveProperty('ETH');
      store.removeIgnoredAssets(['ETH']);

      expect(store.balances.eth['0xacc1'].assets).not.toHaveProperty('ETH');
      expect(store.balances.eth['0xacc1'].assets).toHaveProperty('USDC');
      expect(store.balances.eth['0xacc1'].assets).toHaveProperty('DAI');
      expect(store.balances.eth['0xacc2'].assets).not.toHaveProperty('ETH');
      expect(store.balances.eth['0xacc2'].assets).toHaveProperty('USDT');
      expect(store.balances.btc.bc1q.assets).toHaveProperty('BTC');
    });

    it('should remove assets from both assets and liabilities', () => {
      store.removeIgnoredAssets(['DAI']);

      expect(store.balances.eth['0xacc1'].assets).not.toHaveProperty('DAI');
      expect(store.balances.eth['0xacc1'].liabilities).not.toHaveProperty('DAI');
      expect(Object.keys(store.balances.eth['0xacc1'].liabilities)).toHaveLength(0);
    });

    it('should remove accounts that become empty after filtering', () => {
      store.removeIgnoredAssets(['ETH', 'USDT']);

      expect(store.balances.eth).not.toHaveProperty('0xacc2');
      expect(store.balances.eth).toHaveProperty('0xacc1');
    });

    it('should remove blockchains that become empty after filtering', () => {
      store.removeIgnoredAssets(['BTC']);

      expect(store.balances).not.toHaveProperty('btc');
    });

    it('should handle multiple assets to filter at once', () => {
      store.removeIgnoredAssets(['ETH', 'BTC']);

      expect(store.balances.eth['0xacc1'].assets).not.toHaveProperty('ETH');
      expect(store.balances).not.toHaveProperty('btc');

      expect(store.balances.eth['0xacc1'].assets).toHaveProperty('DAI');
      expect(store.balances.eth['0xacc1'].assets).toHaveProperty('USDC');
    });

    it('should keep blockchain structure intact for non-filtered assets', () => {
      store.removeIgnoredAssets(['NON_EXISTENT_ASSET']);

      expect(Object.keys(store.balances)).toHaveLength(2);
      expect(Object.keys(store.balances.eth)).toHaveLength(2);
    });

    it('should handle case where all assets are filtered out', () => {
      store.removeIgnoredAssets(['ETH', 'BTC', 'DAI', 'USDC', 'USDT']);

      expect(Object.keys(store.balances)).toHaveLength(0);
    });

    it('should handle empty array of assets to filter', () => {
      const balancesBefore = cloneDeep(store.balances);
      store.removeIgnoredAssets([]);
      expect(store.balances).toEqual(balancesBefore);
    });

    it('should preserve value of non-filtered assets', () => {
      store.removeIgnoredAssets(['USDC']);
      expect(store.balances.eth['0xacc1'].assets.ETH.address.value).toEqual(bigNumberify(25000));
    });

    it('should handle filtering with case-sensitive asset names', () => {
      store.removeIgnoredAssets(['eth']); // lowercase
      expect(store.balances.eth['0xacc1'].assets).toHaveProperty('ETH');

      store.removeIgnoredAssets(['ETH']);
      expect(store.balances.eth['0xacc1'].assets).not.toHaveProperty('ETH');
    });
  });
});
