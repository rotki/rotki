import { Blockchain } from '@rotki/common/lib/blockchain';
import { type BtcChains, isBtcChain } from '@/types/blockchain/chains';
import type { MaybeRef } from '@vueuse/core';
import type { AssetBalances } from '@/types/balances';
import type {
  BlockchainBalances,
  BtcBalances,
} from '@/types/blockchain/balances';
import type { AssetPrices } from '@/types/prices';

type Totals = Record<BtcChains, AssetBalances>;

type Balances = Record<BtcChains, BtcBalances>;

function defaultTotals(): Totals {
  return {
    [Blockchain.BTC]: {},
    [Blockchain.BCH]: {},
  };
}

function defaultBtcBalances(): BtcBalances {
  return {
    standalone: {},
    xpubs: [],
  };
}

function defaultBalances(): Balances {
  return {
    [Blockchain.BTC]: defaultBtcBalances(),
    [Blockchain.BCH]: defaultBtcBalances(),
  };
}

export const useBtcBalancesStore = defineStore('balances/btc', () => {
  const balances: Ref<Balances> = ref(defaultBalances());
  const totals: Ref<Totals> = ref(defaultTotals());
  const liabilities: Ref<Totals> = ref(defaultTotals());

  const update = (
    chain: Blockchain,
    { perAccount, totals: updatedTotals }: BlockchainBalances,
  ) => {
    if (!isBtcChain(chain))
      return;

    set(balances, {
      ...get(balances),
      [chain]: perAccount[chain] ?? defaultBtcBalances(),
    });

    set(totals, {
      ...get(totals),
      [chain]: removeZeroAssets(updatedTotals.assets),
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
    updatePrices,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBtcBalancesStore, import.meta.hot));
