import { Blockchain } from '@rotki/common/lib/blockchain';
import { type MaybeRef } from '@vueuse/core';
import { type Ref } from 'vue';
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
  KSM: {},
  DOT: {},
  AVAX: {},
  OPTIMISM: {}
});

const defaultBalances = (): Balances => ({
  KSM: {},
  DOT: {},
  AVAX: {},
  OPTIMISM: {}
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

    const chainValues = perAccount[chain] ?? {};

    set(balances, {
      ...get(balances),
      [chain]: chainValues
    });

    // todo: this is temporary, to update the tokens count
    // todo: remove when BE updates the endpoint to refresh detected tokens
    if (chain === Blockchain.OPTIMISM) {
      const { updateStateOnBalanceRefresh } = useBlockchainTokensStore();

      updateStateOnBalanceRefresh(chain, chainValues);
    }

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
