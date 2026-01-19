import type { ComputedRef, MaybeRef } from 'vue';
import type { EthDetectedTokensInfo } from '@/types/balances';
import { assert } from '@rotki/common';
import { useBalanceQueue } from '@/composables/balances/use-balance-queue';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { arrayify } from '@/utils/array';

interface UseTokenDetectionReturn {
  detectingTokens: ComputedRef<boolean>;
  detectedTokens: ComputedRef<EthDetectedTokensInfo>;
  getEthDetectedTokensInfo: (chain: MaybeRef<string>, address: MaybeRef<string | null>) => ComputedRef<EthDetectedTokensInfo>;
  detectTokens: (addresses?: string[]) => Promise<void>;
  detectTokensOfAllAddresses: () => Promise<void>;
}

export function useTokenDetection(chain: MaybeRef<string | string[]>, accountAddress: MaybeRef<string | null> = null): UseTokenDetectionReturn {
  const { useIsTaskRunning } = useTaskStore();
  const { fetchDetectedTokens: fetchDetectedTokensCaller, getEthDetectedTokensInfo } = useBlockchainTokensStore();
  const { addresses } = useAccountAddresses();
  const { supportsTransactions } = useSupportedChains();
  const { queueTokenDetection } = useBalanceQueue();

  const chains = computed<string[]>(() => arrayify(get(chain)));

  const isDetectingTaskRunning = (blockchain: string, address: string | null): ComputedRef<boolean> =>
    computed(() => get(
      useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
        chain: blockchain,
        ...(address ? { address } : {}),
      }),
    ));

  const detectingTokens = computed<boolean>(() => {
    const address = get(accountAddress);
    return get(chains).some(blockchain => get(isDetectingTaskRunning(blockchain, address)));
  });

  const detectedTokens = computed<EthDetectedTokensInfo>(() => {
    const chainsValue = get(chains);
    let totalTokens = 0;
    let latestTimestamp: number | null = null;
    const allTokens: string[] = [];

    for (const blockchain of chainsValue) {
      const info = get(getEthDetectedTokensInfo(blockchain, accountAddress));
      totalTokens += info.total;
      allTokens.push(...info.tokens);

      if (info.timestamp !== null && (latestTimestamp === null || info.timestamp > latestTimestamp))
        latestTimestamp = info.timestamp;
    }

    return {
      timestamp: latestTimestamp,
      tokens: allTokens,
      total: totalTokens,
    };
  });

  const fetchDetectedTokens = async (blockchain: string, address: string): Promise<void> => {
    assert(supportsTransactions(blockchain));
    await fetchDetectedTokensCaller(blockchain, address);
  };

  const detectTokens = async (addressList: string[] = []): Promise<void> => {
    const address = get(accountAddress);
    assert(address || addressList.length > 0);
    const usedAddresses = address ? [address] : addressList;
    const chainsValue = get(chains);

    await Promise.all(chainsValue.map(async (blockchain) => {
      const filteredAddresses = usedAddresses.filter(addr => !get(isDetectingTaskRunning(blockchain, addr)));
      if (filteredAddresses.length > 0)
        await queueTokenDetection(blockchain, filteredAddresses, async addr => fetchDetectedTokens(blockchain, addr));
    }));
  };

  const detectTokensOfAllAddresses = async (): Promise<void> => {
    const chainsValue = get(chains);
    const addressesValue = get(addresses);

    await Promise.all(chainsValue.map(async (blockchain) => {
      if (!supportsTransactions(blockchain))
        return;

      const tokenAddresses = addressesValue[blockchain] ?? [];

      if (tokenAddresses.length > 0)
        await queueTokenDetection(blockchain, tokenAddresses, async addr => fetchDetectedTokens(blockchain, addr));
    }));
  };

  return {
    detectedTokens,
    detectingTokens,
    detectTokens,
    detectTokensOfAllAddresses,
    getEthDetectedTokensInfo,
  };
}
