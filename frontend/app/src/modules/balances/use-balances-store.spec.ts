import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { bigNumberify, Blockchain } from '@rotki/common';
import { cloneDeep } from 'es-toolkit';
import { beforeEach, describe, expect, it } from 'vitest';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';

describe('useBalancesStore', () => {
  let store: ReturnType<typeof useBalancesStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useBalancesStore();
  });

  it('should update the balance prices and value', () => {
    const { balances } = storeToRefs(store);
    const { updateBalances, updatePrices } = store;
    const assetPrices: AssetPrices = {
      ETH: {
        isManualPrice: false,
        oracle: 'coingecko',
        usdPrice: null,
        value: bigNumberify(2500),
      },
    };

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

    expect(get(balances).eth['0xacc'].assets.ETH.address).toMatchObject({
      amount: bigNumberify(10),
      value: bigNumberify(25000),
    });
  });

  describe('visibleBalances', () => {
    const ETH_BALANCES = (value: number): Parameters<typeof store.updateBalances>[1] => ({
      perAccount: {
        [Blockchain.ETH]: {
          '0xa': {
            assets: { ETH: { address: { amount: bigNumberify(2), value: bigNumberify(value) } } },
            liabilities: {},
          },
        },
      },
      totals: { assets: {}, liabilities: {} },
    });

    function setThreshold(threshold: string | undefined): void {
      useSettingsRepo().updateFrontend({
        balanceValueThreshold: threshold === undefined ? {} : { [BalanceSource.BLOCKCHAIN]: threshold },
      });
    }

    function price(value: number): AssetPrices {
      return { ETH: { isManualPrice: false, oracle: 'coingecko', usdPrice: null, value: bigNumberify(value) } };
    }

    it('should show everything without a threshold', () => {
      store.updateBalances(Blockchain.ETH, ETH_BALANCES(1));
      expect(Object.keys(store.visibleBalances[Blockchain.ETH])).toStrictEqual(['0xa']);
    });

    it('should hide a small balance from the view but keep it in the state', () => {
      setThreshold('100');
      store.updateBalances(Blockchain.ETH, ETH_BALANCES(1));

      expect(store.visibleBalances[Blockchain.ETH]).toStrictEqual({});
      expect(Object.keys(store.balances[Blockchain.ETH])).toStrictEqual(['0xa']);
    });

    it('should show an unpriced balance once its price makes it worth more than the threshold', () => {
      setThreshold('100');
      store.updateBalances(Blockchain.ETH, ETH_BALANCES(0));
      expect(store.visibleBalances[Blockchain.ETH]).toStrictEqual({});

      store.updatePrices(price(2500));

      expect(Object.keys(store.visibleBalances[Blockchain.ETH])).toStrictEqual(['0xa']);
    });

    it('should hide a balance again when a price drop takes it under the threshold', () => {
      setThreshold('100');
      store.updateBalances(Blockchain.ETH, ETH_BALANCES(5000));

      store.updatePrices(price(10));

      expect(store.visibleBalances[Blockchain.ETH]).toStrictEqual({});
    });

    it('should apply a threshold change to what it already holds', () => {
      store.updateBalances(Blockchain.ETH, ETH_BALANCES(50));
      setThreshold('100');
      expect(store.visibleBalances[Blockchain.ETH]).toStrictEqual({});

      setThreshold('10');
      expect(Object.keys(store.visibleBalances[Blockchain.ETH])).toStrictEqual(['0xa']);
    });

    it('should ignore another source\'s threshold', () => {
      useSettingsRepo().updateFrontend({ balanceValueThreshold: { [BalanceSource.EXCHANGES]: '100' } });
      store.updateBalances(Blockchain.ETH, ETH_BALANCES(1));

      expect(Object.keys(store.visibleBalances[Blockchain.ETH])).toStrictEqual(['0xa']);
    });
  });

  it('should revalue each exchange connection without changing its holdings', () => {
    store.exchangeAccountBalances = {
      kraken: {
        main: { ETH: { amount: bigNumberify(2), value: bigNumberify(4000) } },
        trading: { ETH: { amount: bigNumberify(3), value: bigNumberify(6000) } },
      },
    };

    store.updatePrices({
      ETH: { isManualPrice: false, oracle: 'coingecko', usdPrice: null, value: bigNumberify(2500) },
    });

    expect(store.exchangeAccountBalances.kraken).toEqual({
      main: { ETH: { amount: bigNumberify(2), value: bigNumberify(5000) } },
      trading: { ETH: { amount: bigNumberify(3), value: bigNumberify(7500) } },
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
