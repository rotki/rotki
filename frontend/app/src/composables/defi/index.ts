import { type BigNumber, LpType, type XSwapLiquidityBalance } from '@rotki/common';
import { bigNumberSum } from '@/utils/calculation';
import { sortDesc } from '@/utils/bignumbers';
import { useUniswapStore } from '@/store/defi/uniswap';
import { useSushiswapStore } from '@/store/defi/sushiswap';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import type { ComputedRef } from 'vue';

interface UseLiquidityPositionReturn {
  lpAggregatedBalances: ComputedRef<XSwapLiquidityBalance[]>;
  lpTotal: ComputedRef<BigNumber>;
  getPoolName: (type: LpType, assets: string[]) => string;
}

export function useLiquidityPosition(): UseLiquidityPositionReturn {
  const { uniswapV2Balances } = useUniswapStore();
  const { balanceList: sushiswapBalances } = useSushiswapStore();
  const { assetSymbol } = useAssetInfoRetrieval();

  const lpAggregatedBalances = computed<XSwapLiquidityBalance[]>(() => {
    const mappedUniswapV2Balances = get(uniswapV2Balances([])).map((item, index) => ({
      asset: createEvmIdentifierFromAddress(item.address),
      assets: item.assets,
      id: index,
      lpType: LpType.UNISWAP_V2,
      premiumOnly: false,
      type: 'token',
      usdValue: item.userBalance.usdValue,
    }) satisfies XSwapLiquidityBalance);

    const mappedSushiswapBalances = get(sushiswapBalances([])).map((item, index) => ({
      asset: createEvmIdentifierFromAddress(item.address),
      assets: item.assets,
      id: index,
      lpType: LpType.SUSHISWAP,
      premiumOnly: true,
      type: 'token',
      usdValue: item.userBalance.usdValue,
    }) satisfies XSwapLiquidityBalance);

    return [
      ...mappedUniswapV2Balances,
      ...mappedSushiswapBalances,
    ].sort((a, b) => sortDesc(a.usdValue, b.usdValue)).map((item, id) => ({ ...item, id }));
  });

  const lpTotal = computed<BigNumber>(() => bigNumberSum(get(lpAggregatedBalances).map(item => item.usdValue)));

  const getPoolName = (type: LpType, assets: string[]): string => {
    const concatAssets = (assets: string[]): string => assets.map(asset => get(assetSymbol(asset))).join('/');

    const data = [{
      identifier: LpType.UNISWAP_V2,
      name: (assets: string[]): string => `UNIv2 ${concatAssets(assets)}`,
    }, {
      identifier: LpType.SUSHISWAP,
      name: (assets: string[]): string => `SLP ${concatAssets(assets)}`,
    }];

    const selected = data.find(({ identifier }) => identifier === get(type));

    if (!selected)
      return concatAssets(assets);

    return selected.name(get(assets));
  };

  return {
    getPoolName,
    lpAggregatedBalances,
    lpTotal,
  };
}
