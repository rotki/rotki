import { cloneDeep, isEqual } from 'es-toolkit';
import { useBlockchainStore } from '@/store/blockchain/index';
import { usePremium } from '@/composables/premium';
import { fetchDataAsync } from '@/utils/fetch-async';
import { Module } from '@/types/modules';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatusStore } from '@/store/status';
import { balanceSum, bigNumberSum } from '@/utils/calculation';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { sortDesc } from '@/utils/bignumbers';
import { usePoolApi } from './use-pool-api';
import { usePoolBalancesStore } from './use-pool-balances-store';
import { type PoolBalance, PoolBalances, type PoolLiquidityBalance, PoolType } from './types';
import type { OnError } from '@/types/fetch';
import type { TaskMeta } from '@/types/task';
import type { BigNumber, Writeable } from '@rotki/common';
import type { ComputedRef } from 'vue';

function updateExistingBalance(existingBalance: Writeable<PoolBalance>, newBalance: PoolBalance): void {
  existingBalance.userBalance = balanceSum(
    existingBalance.userBalance,
    newBalance.userBalance,
  );

  newBalance.assets.forEach((newAsset) => {
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
  });
}

function createNewBalance(account: string, poolBalance: PoolBalance): Writeable<PoolBalance> {
  return {
    account,
    address: poolBalance.address,
    assets: poolBalance.assets,
    nftId: poolBalance.nftId,
    priceRange: poolBalance.priceRange,
    totalSupply: poolBalance.totalSupply,
    userBalance: poolBalance.userBalance,
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
  const chainStore = useBlockchainStore();
  const ethAddresses = computed<string[]>(() => chainStore.getAddresses(Blockchain.ETH));

  const { sushiswapPoolBalances, uniswapPoolBalances } = storeToRefs(usePoolBalancesStore());
  const { activeModules } = storeToRefs(useGeneralSettingsStore());

  const premium = usePremium();
  const { t } = useI18n();
  const { isLoading } = useStatusStore();
  const { getSushiswapBalances, getUniswapV2Balances } = usePoolApi();
  const { assetSymbol } = useAssetInfoRetrieval();

  const loading = logicOr(
    isLoading(Section.POOLS_UNISWAP_V2),
    isLoading(Section.POOLS_SUSHISWAP),
  );

  const balances = computed<PoolLiquidityBalance[]>(() => {
    const uniswap = toArray(get(uniswapPoolBalances));
    const sushiswap = toArray(get(sushiswapPoolBalances));

    const uniswapBalances = uniswap.map((item, index) => ({
      asset: createEvmIdentifierFromAddress(item.address),
      assets: item.assets,
      id: index,
      premiumOnly: false,
      type: PoolType.UNISWAP_V2,
      usdValue: item.userBalance.usdValue,
    }) satisfies PoolLiquidityBalance);

    const sushiswapBalances = sushiswap.map((item, index) => ({
      asset: createEvmIdentifierFromAddress(item.address),
      assets: item.assets,
      id: index,
      premiumOnly: true,
      type: PoolType.SUSHISWAP,
      usdValue: item.userBalance.usdValue,
    }) satisfies PoolLiquidityBalance);

    return [
      ...uniswapBalances,
      ...sushiswapBalances,
    ].sort((a, b) => sortDesc(a.usdValue, b.usdValue)).map((item, id) => ({ ...item, id }));
  });

  const total = computed<BigNumber>(() => bigNumberSum(get(balances).map(item => item.usdValue)));

  const getPoolName = (type: PoolType, assets: string[]): string => {
    const concatAssets = (assets: string[]): string => assets.map(asset => get(assetSymbol(asset))).join('-');

    const data = [{
      identifier: PoolType.UNISWAP_V2,
      name: (assets: string[]): string => `UNI-V2 ${concatAssets(assets)}`,
    }, {
      identifier: PoolType.SUSHISWAP,
      name: (assets: string[]): string => `SLP ${concatAssets(assets)}`,
    }] as const;

    const selected = data.find(({ identifier }) => identifier === get(type));

    if (!selected)
      return concatAssets(assets);

    return selected.name(get(assets));
  };

  function toArray(poolBalances: PoolBalances): PoolBalance[] {
    const aggregatedBalances: Record<string, Writeable<PoolBalance>> = {};

    for (const account in poolBalances) {
      const accountBalances = cloneDeep(poolBalances)[account];
      if (!accountBalances || accountBalances.length === 0)
        continue;

      for (const poolBalance of accountBalances) {
        const { address } = poolBalance;

        const existingAddress = Object.keys(aggregatedBalances).find(key => key.toLowerCase() === address.toLowerCase());

        if (existingAddress) {
          updateExistingBalance(aggregatedBalances[existingAddress], poolBalance);
        }
        else {
          aggregatedBalances[address] = createNewBalance(account, poolBalance);
        }
      }
    }
    return Object.values(aggregatedBalances);
  }

  const retrieveSushiswapBalances = async (refresh = false): Promise<void> => {
    const protocol = 'Sushiswap';
    const title = t('modules.dashboard.liquidity_pools.task.title', { protocol });
    const meta: TaskMeta = { title };

    const onError: OnError = {
      error: message => t('modules.dashboard.liquidity_pools.task.error_message', { message, protocol }),
      title,
    };

    await fetchDataAsync({
      refresh,
      requires: {
        module: Module.SUSHISWAP,
        premium: true,
      },
      state: {
        activeModules,
        isPremium: premium,
      },
      task: {
        meta,
        onError,
        parser: data => PoolBalances.parse(data),
        query: async () => getSushiswapBalances(),
        section: Section.POOLS_SUSHISWAP,
        type: TaskType.SUSHISWAP_BALANCES,
      },
    }, sushiswapPoolBalances);
  };

  const retrieveUniswapV2Balances = async (refresh = false): Promise<void> => {
    const protocol = 'Uniswap V2';
    const title = t('modules.dashboard.liquidity_pools.task.title', { protocol });
    const meta: TaskMeta = { title };

    const onError: OnError = {
      error: message => t('modules.dashboard.liquidity_pools.task.error_message', { message, protocol }),
      title,
    };

    await fetchDataAsync({
      refresh,
      requires: {
        module: Module.UNISWAP,
        premium: false,
      },
      state: {
        activeModules,
        isPremium: premium,
      },
      task: {
        meta,
        onError,
        parser: data => PoolBalances.parse(data),
        query: async () => getUniswapV2Balances(),
        section: Section.POOLS_UNISWAP_V2,
        type: TaskType.UNISWAP_V2_BALANCES,
      },
    }, uniswapPoolBalances);
  };

  async function fetch(refresh = false): Promise<void> {
    if (get(ethAddresses).length <= 0) {
      return;
    }

    await retrieveUniswapV2Balances(refresh);
    if (!get(premium)) {
      return;
    }
    await retrieveSushiswapBalances(refresh);
  }

  watch(ethAddresses, async (addresses, previousAddresses) => {
    if (!isEqual(addresses, previousAddresses))
      await fetch(true);
  });

  watch(premium, async (isActive, wasActive) => {
    if (wasActive !== isActive)
      await fetch(true);
  });

  return {
    balances,
    fetch,
    getPoolName,
    loading,
    total,
  };
}
