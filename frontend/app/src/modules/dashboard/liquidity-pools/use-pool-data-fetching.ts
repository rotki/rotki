import { Blockchain } from '@rotki/common';
import { createSharedComposable } from '@vueuse/core';
import { get } from '@vueuse/shared';
import { isEqual } from 'es-toolkit';
import { storeToRefs } from 'pinia';
import { computed, watch } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { Module } from '@/modules/core/common/modules';
import { usePremium } from '@/modules/premium/use-premium';
import { ActivityPart } from '@/modules/task-center/core/types';
import { usePoolApi } from './use-pool-api';
import { usePoolBalancesStore } from './use-pool-balances-store';
import { type PoolProtocol, usePoolProtocolQuery } from './use-pool-protocol-query';

interface UsePoolDataFetchingReturn {
  fetch: (refresh?: boolean) => Promise<void>;
}

/**
 * Shared, so the pool table and the dashboard refresh menu drive one fetcher: its watchers refetch on
 * account and premium changes, and a second instance would run every refetch twice.
 */
export const usePoolDataFetching = createSharedComposable((): UsePoolDataFetchingReturn => {
  const { addresses } = useAccountAddresses();
  const ethAddresses = computed<string[]>(() => get(addresses)[Blockchain.ETH] ?? []);

  const { sushiswapPoolBalances, uniswapPoolBalances } = storeToRefs(usePoolBalancesStore());
  const { recentlyAddedAddresses } = storeToRefs(useBlockchainAccountsStore());

  const premium = usePremium();

  const { getSushiswapBalances, getUniswapV2Balances } = usePoolApi();
  const { retrievePoolBalances } = usePoolProtocolQuery();

  const uniswapV2: PoolProtocol = {
    label: 'Uniswap V2',
    module: Module.UNISWAP,
    part: ActivityPart.UNISWAP_V2,
    query: getUniswapV2Balances,
    target: uniswapPoolBalances,
  };

  const sushiswap: PoolProtocol = {
    label: 'Sushiswap',
    module: Module.SUSHISWAP,
    part: ActivityPart.SUSHISWAP,
    query: getSushiswapBalances,
    target: sushiswapPoolBalances,
  };

  async function fetch(refresh = false): Promise<void> {
    if (get(ethAddresses).length === 0)
      return;

    await retrievePoolBalances(uniswapV2, refresh);
    if (!get(premium))
      return;

    await retrievePoolBalances(sushiswap, refresh);
  }

  watch(ethAddresses, async (current, previous) => {
    if (isEqual(current, previous))
      return;

    const added = current.filter(a => !previous.includes(a));
    const removed = previous.filter(a => !current.includes(a));
    const recent = get(recentlyAddedAddresses);

    if (removed.length === 0 && added.length > 0 && added.every(a => recent.has(a)))
      return;

    await fetch(true);
  });

  watch(premium, async (isActive, wasActive) => {
    if (wasActive !== isActive)
      await fetch(true);
  });

  return {
    fetch,
  };
});
