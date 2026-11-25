import type { PoolBalances } from './types';
import { defineStore } from 'pinia';
import { ref } from 'vue';

export const usePoolBalancesStore = defineStore('poolBalances', () => {
  const uniswapPoolBalances = ref<PoolBalances>({});
  const sushiswapPoolBalances = ref<PoolBalances>({});

  return {
    sushiswapPoolBalances,
    uniswapPoolBalances,
  };
});
