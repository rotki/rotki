import { Blockchain } from '@rotki/common/lib/blockchain';
import { MaybeRef } from '@vueuse/core';
import { Ref } from 'vue';
import { AssetBalances } from '@/types/balances';
import {
  BlockchainAssetBalances,
  BlockchainBalances
} from '@/types/blockchain/balances';
import { isRestChain, RestChains } from '@/types/blockchain/chains';
import { AssetPrices } from '@/types/prices';
import { removeZeroAssets } from '@/utils/balances';
import {
  updateBlockchainAssetBalances,
  updateTotalsPrices
} from '@/utils/prices';

type Totals = Record<RestChains, AssetBalances>;
type Balances = Record<RestChains, BlockchainAssetBalances>;

const defaultTotals = (): Totals => ({
  KSM: {},
  DOT: {},
  AVAX: {}
});

const defaultBalances = (): Balances => ({
  KSM: {},
  DOT: {},
  AVAX: {}
});

export const useChainBalancesStore = defineStore('balances/chain', () => {
  const balances: Ref<Balances> = ref(defaultBalances());
  const totals: Ref<Totals> = ref(defaultTotals());
  const liabilities: Ref<Totals> = ref(defaultTotals());

  const update = (
    chain: Blockchain,
    { perAccount, totals: updatedTotals }: BlockchainBalances
  ) => {
    if (!isRestChain(chain)) {
      return;
    }

    set(balances, {
      ...get(balances),
      [chain]: perAccount[chain] ?? {}
    });

    set(totals, {
      ...get(totals),
      [chain]: removeZeroAssets(updatedTotals.assets)
    });

    set(liabilities, {
      ...get(liabilities),
      [chain]: removeZeroAssets(updatedTotals.liabilities)
    });
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>) => {
    set(totals, updateTotalsPrices(totals, prices));
    set(liabilities, updateTotalsPrices(liabilities, prices));
    set(balances, updateBlockchainAssetBalances(balances, prices));
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
  import.meta.hot.accept(
    acceptHMRUpdate(useChainBalancesStore, import.meta.hot)
  );
}
