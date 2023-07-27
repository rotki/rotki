import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import camelCase from 'lodash/camelCase';
import { type AssetBalances } from '@/types/balances';
import {
  type BlockchainAssetBalances,
  type BlockchainBalances
} from '@/types/blockchain/balances';
import { type RestChains, isRestChain } from '@/types/blockchain/chains';
import { type AssetPrices } from '@/types/prices';

type Totals = Record<RestChains, AssetBalances>;

type Balances = Record<RestChains, BlockchainAssetBalances>;

const defaultTotals = (): Totals => ({
  [Blockchain.KSM]: {},
  [Blockchain.DOT]: {},
  [Blockchain.AVAX]: {},
  [Blockchain.OPTIMISM]: {},
  [Blockchain.POLYGON_POS]: {},
  [Blockchain.ARBITRUM_ONE]: {}
});

const defaultBalances = (): Balances => ({
  [Blockchain.KSM]: {},
  [Blockchain.DOT]: {},
  [Blockchain.AVAX]: {},
  [Blockchain.OPTIMISM]: {},
  [Blockchain.POLYGON_POS]: {},
  [Blockchain.ARBITRUM_ONE]: {}
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
      [chain]: perAccount[camelCase(chain)] ?? {}
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
