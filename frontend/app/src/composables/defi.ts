import { BigNumber } from '@rotki/common';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { bigNumberSum } from '@/filters';
import { useBalancerStore } from '@/store/defi/balancer';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useUniswapStore } from '@/store/defi/uniswap';
import { sortDesc } from '@/utils/bignumbers';

export const setupLiquidityPosition = () => {
  const { uniswapV2Balances, uniswapV3Balances } = useUniswapStore();
  const { balanceList: sushiswapBalances } = useSushiswapStore();
  const { balanceList: balancerBalances } = storeToRefs(useBalancerStore());

  const lpAggregatedBalances = (includeNft: boolean = true) =>
    computed(() => {
      const mappedUniswapV3Balances = get(uniswapV3Balances([])).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue,
        asset: item.nftId,
        premiumOnly: true,
        type: 'nft'
      }));

      const mappedUniswapV2Balances = get(uniswapV2Balances([])).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue,
        asset: `_ceth_${item.address}`,
        premiumOnly: false,
        type: 'token'
      }));

      const mappedSushiswapBalances = get(sushiswapBalances([])).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue,
        asset: `_ceth_${item.address}`,
        premiumOnly: true,
        type: 'token'
      }));

      const mappedBalancerBalances = get(balancerBalances).map(item => ({
        ...item,
        usdValue: item.userBalance.usdValue as BigNumber,
        asset: `_ceth_${item.address}`,
        premiumOnly: true,
        assets: item.tokens.map(asset => ({
          ...asset,
          asset: asset.token
        })),
        type: 'token'
      }));

      return [
        ...(includeNft ? mappedUniswapV3Balances : []),
        ...mappedUniswapV2Balances,
        ...mappedSushiswapBalances,
        ...mappedBalancerBalances
      ]
        .sort((a, b) => sortDesc(a.usdValue, b.usdValue))
        .map((item, id) => ({ ...item, id }));
    });

  const lpTotal = (includeNft: boolean = false) =>
    computed<BigNumber>(() => {
      return bigNumberSum(
        get(lpAggregatedBalances(includeNft)).map(item => item.usdValue)
      );
    });

  return {
    lpAggregatedBalances,
    lpTotal
  };
};
