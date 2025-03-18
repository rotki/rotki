import type { AssetPrices } from '@/types/prices';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { bigNumberify, Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it } from 'vitest';

describe('useBalancesStore', () => {
  let store: ReturnType<typeof useBalancesStore>;

  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    store = useBalancesStore();
  });

  it('should update the balance prices and usd value', () => {
    const { updateBalances, updatePrices } = store;
    const assetPrices: AssetPrices = {
      ETH: {
        isManualPrice: false,
        usdPrice: null,
        value: bigNumberify(2500),
      },
    };

    updateBalances(Blockchain.ETH, {
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

    updatePrices(assetPrices);

    expect(store.balances.eth['0xacc'].assets.ETH).toEqual({
      amount: bigNumberify(10),
      usdValue: bigNumberify(25000),
    });
  });
});
