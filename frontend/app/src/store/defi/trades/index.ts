import { DexTrade } from '@rotki/common/lib/defi/dex';
import { computed, ComputedRef } from '@vue/composition-api';
import { get } from '@vueuse/core';
import sortBy from 'lodash/sortBy';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { useBalancerStore } from '@/store/defi/balancer';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { DexTrades } from '@/store/defi/types';
import { useUniswapStore } from '@/store/defi/uniswap';

const addTrades = (
  dexTrades: DexTrades,
  addresses: string[],
  trades: DexTrade[]
) => {
  for (const address in dexTrades) {
    if (addresses.length > 0 && !addresses.includes(address)) {
      continue;
    }
    trades.push(...dexTrades[address]);
  }
};

export const useDexTradesStore = defineStore('defi/trades', () => {
  const balancerStore = useBalancerStore();
  const sushiswapStore = useSushiswapStore();
  const uniswapStore = useUniswapStore();

  const { trades: uniswapTrades } = storeToRefs(uniswapStore);
  const { trades: sushiswapTrades } = storeToRefs(sushiswapStore);
  const { trades: balancerTrades } = storeToRefs(balancerStore);

  const dexTrades = (addresses: string[]): ComputedRef<DexTrade[]> =>
    computed(() => {
      const trades: DexTrade[] = [];

      addTrades(get(uniswapTrades) as DexTrades, addresses, trades);
      addTrades(get(balancerTrades) as DexTrades, addresses, trades);
      const sushi = get(sushiswapTrades) as DexTrades;
      if (sushi && Object.keys(sushi).length > 0) {
        addTrades(sushi, addresses, trades);
      }

      return sortBy(trades, 'timestamp').reverse();
    });

  return {
    dexTrades
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useDexTradesStore, import.meta.hot));
}
