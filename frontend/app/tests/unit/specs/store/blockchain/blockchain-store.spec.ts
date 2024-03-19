import { beforeEach, describe } from 'vitest';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { useBlockchainStore } from '@/store/blockchain';
import type { AssetPrices } from '@/types/prices';

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
          usdPrice: null,
          isManualPrice: false,
          isCurrentCurrency: true,
        },
      };

      store.updateBalances(Blockchain.ETH, {
        perAccount: {
          [Blockchain.ETH]: {
            '0xacc': {
              assets: {
                ETH: {
                  amount: bigNumberify(10),
                  usdValue: bigNumberify(20000),
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
              usdValue: bigNumberify(20000),
            },
          },
          liabilities: {},
        },
      });

      store.updatePrices(assetPrices);

      expect(store.totals.eth.ETH).toEqual({
        amount: bigNumberify(10),
        usdValue: bigNumberify(25000),
      });

      expect(store.balances.eth['0xacc'].assets.ETH).toEqual({
        amount: bigNumberify(10),
        usdValue: bigNumberify(25000),
      });
    });
  });
});
