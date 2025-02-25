import type { PoolBalances } from './types';

export const usePoolBalancesStore = defineStore('poolBalances', () => {
  const uniswapPoolBalances = ref<PoolBalances>({});
  const sushiswapPoolBalances = ref<PoolBalances>({});

  return {
    sushiswapPoolBalances,
    uniswapPoolBalances,
  };
});
