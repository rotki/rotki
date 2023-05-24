import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { type Ref } from 'vue';
import { type AssetBalances } from '@/types/balances';
import {
  type BlockchainBalances,
  type BtcBalances
} from '@/types/blockchain/balances';
import { type BtcChains, isBtcChain } from '@/types/blockchain/chains';
import { type AssetPrices } from '@/types/prices';

type Totals = Record<BtcChains, AssetBalances>;
type Balances = Record<BtcChains, BtcBalances>;

const defaultTotals = (): Totals => ({
  [Blockchain.BTC]: {},
  [Blockchain.BCH]: {}
});

const defaultBtcBalances = (): BtcBalances => ({
  standalone: {},
  xpubs: []
});

const defaultBalances = (): Balances => ({
  [Blockchain.BTC]: defaultBtcBalances(),
  [Blockchain.BCH]: defaultBtcBalances()
});

export const useBtcBalancesStore = defineStore('balances/btc', () => {
  const balances: Ref<Balances> = ref(defaultBalances());
  const totals: Ref<Totals> = ref(defaultTotals());
  const liabilities: Ref<Totals> = ref(defaultTotals());

  const update = (
    chain: Blockchain,
    { perAccount, totals: updatedTotals }: BlockchainBalances
  ) => {
    if (!isBtcChain(chain)) {
      return;
    }

    set(balances, {
      ...get(balances),
      [chain]: perAccount[chain] ?? defaultBtcBalances()
    });

    set(totals, {
      ...get(totals),
      [chain]: removeZeroAssets(updatedTotals.assets)
    });
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>) => {
    set(totals, updateTotalsPrices(totals, prices));
    set(liabilities, updateTotalsPrices(liabilities, prices));
    set(balances, updateBtcPrices(balances, prices));
  };

  return {
    balances,
    totals,
    liabilities,
    update,
    updatePrices
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBtcBalancesStore, import.meta.hot));
}
