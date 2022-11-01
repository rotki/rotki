import { Blockchain } from '@rotki/common/lib/blockchain';
import { MaybeRef } from '@vueuse/core';
import { Ref } from 'vue';
import { AssetBalances } from '@/types/balances';
import { BlockchainBalances, BtcBalances } from '@/types/blockchain/balances';
import { BtcChains, isBtcChain } from '@/types/blockchain/chains';
import { AssetPrices } from '@/types/prices';
import { removeZeroAssets } from '@/utils/balances';
import { updateBtcPrices, updateTotalsPrices } from '@/utils/prices';

type Totals = Record<BtcChains, AssetBalances>;
type Balances = Record<BtcChains, BtcBalances>;

const defaultTotals = (): Totals => ({
  BTC: {},
  BCH: {}
});

const defaultBtcBalances = (): BtcBalances => ({
  standalone: {},
  xpubs: []
});

const defaultBalances = (): Balances => ({
  BTC: defaultBtcBalances(),
  BCH: defaultBtcBalances()
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
