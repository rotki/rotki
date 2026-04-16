import type { ComputedRef } from 'vue';
import { type BigNumber, createEvmIdentifierFromAddress, type Writeable } from '@rotki/common';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSectionStatus } from '@/composables/status';
import { sortDesc } from '@/modules/common/data/bignumbers';
import { balanceSum, bigNumberSum } from '@/modules/common/data/calculation';
import { Section } from '@/modules/common/status';
import { type PoolBalance, type PoolBalances, type PoolLiquidityBalance, PoolType } from './types';
import { usePoolBalancesStore } from './use-pool-balances-store';
import { usePoolDataFetching } from './use-pool-data-fetching';

function updateExistingBalance(existingBalance: Writeable<PoolBalance>, newBalance: PoolBalance): void {
  existingBalance.userBalance = balanceSum(
    existingBalance.userBalance,
    newBalance.userBalance,
  );

  for (const newAsset of newBalance.assets) {
    const existingAssetIndex = existingBalance.assets.findIndex(item => item.asset === newAsset.asset);

    if (existingAssetIndex > -1) {
      const existingAsset = existingBalance.assets[existingAssetIndex];
      existingBalance.assets[existingAssetIndex] = {
        ...existingAsset,
        userBalance: balanceSum(existingAsset.userBalance, newAsset.userBalance),
      };
    }
    else {
      existingBalance.assets.push(newAsset);
    }
  }
}

function createNewBalance(account: string, poolBalance: PoolBalance): Writeable<PoolBalance> {
  return {
    ...poolBalance,
    account,
    assets: [...poolBalance.assets],
  };
}

interface UsePoolBalancesReturn {
  balances: ComputedRef<PoolLiquidityBalance[]>;
  fetch: (refresh?: boolean) => Promise<void>;
  getPoolName: (type: PoolType, assets: string[]) => string;
  loading: ComputedRef<boolean>;
  total: ComputedRef<BigNumber>;
}

export function usePoolBalances(): UsePoolBalancesReturn {
  const { sushiswapPoolBalances, uniswapPoolBalances } = storeToRefs(usePoolBalancesStore());
  const { getAssetField } = useAssetInfoRetrieval();
  const { fetch } = usePoolDataFetching();

  const { isLoading: uniswapLoading } = useSectionStatus(Section.POOLS_UNISWAP_V2);
  const { isLoading: sushiswapLoading } = useSectionStatus(Section.POOLS_SUSHISWAP);
  const loading = logicOr(uniswapLoading, sushiswapLoading);

  function toArray(poolBalances: PoolBalances): PoolBalance[] {
    const aggregatedBalances = new Map<string, Writeable<PoolBalance>>();

    for (const account in poolBalances) {
      const accountBalances = poolBalances[account];
      if (!accountBalances || accountBalances.length === 0)
        continue;

      for (const poolBalance of accountBalances) {
        const key = poolBalance.address.toLowerCase();
        const existing = aggregatedBalances.get(key);

        if (existing) {
          updateExistingBalance(existing, poolBalance);
        }
        else {
          aggregatedBalances.set(key, createNewBalance(account, poolBalance));
        }
      }
    }
    return [...aggregatedBalances.values()];
  }

  function mapPoolBalances(items: PoolBalance[], type: PoolType, premiumOnly: boolean): PoolLiquidityBalance[] {
    return items.map((item, index) => ({
      asset: createEvmIdentifierFromAddress(item.address),
      assets: item.assets,
      id: index,
      premiumOnly,
      type,
      value: item.userBalance.value,
    }));
  }

  const balances = computed<PoolLiquidityBalance[]>(() => {
    const uniswapBalances = mapPoolBalances(toArray(get(uniswapPoolBalances)), PoolType.UNISWAP_V2, false);
    const sushiswapBalances = mapPoolBalances(toArray(get(sushiswapPoolBalances)), PoolType.SUSHISWAP, true);

    return [
      ...uniswapBalances,
      ...sushiswapBalances,
    ].sort((a, b) => sortDesc(a.value, b.value)).map((item, id) => ({ ...item, id }));
  });

  const total = computed<BigNumber>(() => bigNumberSum(get(balances).map(item => item.value)));

  function getPoolName(type: PoolType, assets: string[]): string {
    const concatAssets = (items: string[]): string => items.map(asset => getAssetField(asset, 'symbol')).join('-');

    const prefixes: Record<string, string> = {
      [PoolType.UNISWAP_V2]: 'UNI-V2',
      [PoolType.SUSHISWAP]: 'SLP',
    };

    const prefix = prefixes[type];
    const joined = concatAssets(assets);
    return prefix ? `${prefix} ${joined}` : joined;
  }

  return {
    balances,
    fetch,
    getPoolName,
    loading,
    total,
  };
}
