import { TaskType } from '@/types/task-type';
import type { MaybeRef } from '@vueuse/core';

export function useTokenDetection(chain: MaybeRef<string>, accountAddress: MaybeRef<string | null> = null) {
  const { isTaskRunning } = useTaskStore();
  const { getEthDetectedTokensInfo, fetchDetectedTokens: fetchDetectedTokensCaller } = useBlockchainTokensStore();
  const { addresses } = useBlockchainStore();
  const { supportsTransactions } = useSupportedChains();

  const isDetectingTaskRunning = (address: string | null) =>
    computed(() =>
      get(
        isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
          chain: get(chain),
          ...(address ? { address } : {}),
        }),
      ),
    );

  const detectingTokens = computed<boolean>(() => {
    const address = get(accountAddress);
    return get(isDetectingTaskRunning(address));
  });

  const detectedTokens = getEthDetectedTokensInfo(chain, accountAddress);

  const fetchDetectedTokens = async (address: string) => {
    const blockchain = get(chain);
    assert(supportsTransactions(blockchain));
    await fetchDetectedTokensCaller(blockchain, address);
  };

  const detectTokens = async (addresses: string[] = []) => {
    const address = get(accountAddress);
    assert(address || addresses.length > 0);
    const usedAddresses = (address ? [address] : addresses).filter(address => !get(isDetectingTaskRunning(address)));
    await awaitParallelExecution(usedAddresses, item => item, fetchDetectedTokens, 2);
  };

  const detectTokensOfAllAddresses = async () => {
    const blockchain = get(chain);
    if (!supportsTransactions(chain))
      return;

    const tokenAddresses = get(addresses)[blockchain] ?? [];

    if (tokenAddresses.length > 0)
      await detectTokens(tokenAddresses);
  };

  return {
    detectingTokens,
    detectedTokens,
    getEthDetectedTokensInfo,
    detectTokens,
    detectTokensOfAllAddresses,
  };
}
