import { type BigNumber, LpType, type XSwapLiquidityBalance } from '@rotki/common';

interface UseLiquidityPositionReturn {
  lpAggregatedBalances: (includeNft?: boolean) => ComputedRef<XSwapLiquidityBalance[]>;
  lpTotal: (includeNft?: boolean) => ComputedRef<BigNumber>;
  getPoolName: (type: LpType, assets: string[]) => string;
}

export function useLiquidityPosition(): UseLiquidityPositionReturn {
  const { uniswapV2Balances, uniswapV3Balances } = useUniswapStore();
  const { balanceList: sushiswapBalances } = useSushiswapStore();
  const { balancerBalances } = useBalancerStore();
  const { assetSymbol } = useAssetInfoRetrieval();

  const lpAggregatedBalances = (
    includeNft = true,
  ): ComputedRef<XSwapLiquidityBalance[]> => computed<XSwapLiquidityBalance[]>(() => {
    const mappedUniswapV3Balances = get(uniswapV3Balances([])).map((item, index) => ({
      id: index,
      assets: item.assets,
      usdValue: item.userBalance.usdValue,
      asset: item.nftId || '',
      premiumOnly: true,
      type: 'nft',
      lpType: LpType.UNISWAP_V3,
    }) satisfies XSwapLiquidityBalance);

    const mappedUniswapV2Balances = get(uniswapV2Balances([])).map((item, index) => ({
      id: index,
      assets: item.assets,
      usdValue: item.userBalance.usdValue,
      asset: createEvmIdentifierFromAddress(item.address),
      premiumOnly: false,
      type: 'token',
      lpType: LpType.UNISWAP_V2,
    }) satisfies XSwapLiquidityBalance);

    const mappedSushiswapBalances = get(sushiswapBalances([])).map((item, index) => ({
      id: index,
      assets: item.assets,
      usdValue: item.userBalance.usdValue,
      asset: createEvmIdentifierFromAddress(item.address),
      premiumOnly: true,
      type: 'token',
      lpType: LpType.SUSHISWAP,
    }) satisfies XSwapLiquidityBalance);

    const mappedBalancerBalances = get(balancerBalances([])).map((item, index) => ({
      id: index,
      usdValue: item.userBalance.usdValue,
      asset: createEvmIdentifierFromAddress(item.address),
      premiumOnly: true,
      assets: item.tokens.map(asset => ({
        ...asset,
        asset: asset.token,
      })),
      type: 'token',
      lpType: LpType.BALANCER,
    }) satisfies XSwapLiquidityBalance);

    return [
      ...(includeNft ? mappedUniswapV3Balances : []),
      ...mappedUniswapV2Balances,
      ...mappedSushiswapBalances,
      ...mappedBalancerBalances,
    ].sort((a, b) => sortDesc(a.usdValue, b.usdValue))
      .map((item, id) => ({ ...item, id }));
  });

  const lpTotal = (includeNft = false): ComputedRef<BigNumber> =>
    computed<BigNumber>(() => bigNumberSum(get(lpAggregatedBalances(includeNft)).map(item => item.usdValue)));

  const getPoolName = (type: LpType, assets: string[]): string => {
    const concatAssets = (assets: string[]): string => assets.map(asset => get(assetSymbol(asset))).join('/');

    const data = [{
      identifier: LpType.UNISWAP_V2,
      name: (assets: string[]): string => `UNIv2 ${concatAssets(assets)}`,
    }, {
      identifier: LpType.UNISWAP_V3,
      name: (assets: string[]): string => `UNIv3 ${concatAssets(assets)}`,
    }, {
      identifier: LpType.SUSHISWAP,
      name: (assets: string[]): string => `SLP ${concatAssets(assets)}`,
    }, {
      identifier: LpType.BALANCER,
      name: (assets: string[]): string => concatAssets(assets),
    }];

    const selected = data.find(({ identifier }) => identifier === get(type));

    if (!selected)
      return concatAssets(assets);

    return selected.name(get(assets));
  };

  return {
    lpAggregatedBalances,
    lpTotal,
    getPoolName,
  };
}
