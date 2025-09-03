import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { EthDetectedTokensInfo } from '@/types/balances';
import { assert } from '@rotki/common';
import { useSupportedChains } from '@/composables/info/chains';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { useBalanceQueueStore } from '@/store/balances/balance-queue';
import { useBlockchainTokensStore } from '@/store/blockchain/tokens';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

interface UseTokenDetectionReturn {
  detectingTokens: ComputedRef<boolean>;
  detectedTokens: ComputedRef<EthDetectedTokensInfo>;
  getEthDetectedTokensInfo: (chain: MaybeRef<string>, address: MaybeRef<string | null>) => ComputedRef<EthDetectedTokensInfo>;
  detectTokens: (addresses?: string[]) => Promise<void>;
  detectTokensOfAllAddresses: () => Promise<void>;
}

export function useTokenDetection(chain: MaybeRef<string>, accountAddress: MaybeRef<string | null> = null): UseTokenDetectionReturn {
  const { useIsTaskRunning } = useTaskStore();
  const { fetchDetectedTokens: fetchDetectedTokensCaller, getEthDetectedTokensInfo } = useBlockchainTokensStore();
  const { addresses } = useAccountAddresses();
  const { supportsTransactions } = useSupportedChains();

  const isDetectingTaskRunning = (address: string | null): ComputedRef<boolean> =>
    computed(() => get(
      useIsTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
        chain: get(chain),
        ...(address ? { address } : {}),
      }),
    ));

  const detectingTokens = computed<boolean>(() => {
    const address = get(accountAddress);
    return get(isDetectingTaskRunning(address));
  });

  const detectedTokens = getEthDetectedTokensInfo(chain, accountAddress);

  const fetchDetectedTokens = async (address: string): Promise<void> => {
    const blockchain = get(chain);
    assert(supportsTransactions(blockchain));
    await fetchDetectedTokensCaller(blockchain, address);
  };

  const detectTokens = async (addresses: string[] = []): Promise<void> => {
    const address = get(accountAddress);
    assert(address || addresses.length > 0);
    const usedAddresses = (address ? [address] : addresses).filter(address => !get(isDetectingTaskRunning(address)));

    const blockchain = get(chain);
    const { queueTokenDetection } = useBalanceQueueStore();
    await queueTokenDetection(blockchain, usedAddresses, fetchDetectedTokens);
  };

  const detectTokensOfAllAddresses = async (): Promise<void> => {
    const blockchain = get(chain);
    if (!supportsTransactions(chain))
      return;

    const tokenAddresses = get(addresses)[blockchain] ?? [];

    if (tokenAddresses.length > 0)
      await detectTokens(tokenAddresses);
  };

  return {
    detectedTokens,
    detectingTokens,
    detectTokens,
    detectTokensOfAllAddresses,
    getEthDetectedTokensInfo,
  };
}
