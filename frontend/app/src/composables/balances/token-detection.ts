import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';
import type { MaybeRef } from '@vueuse/core';

export function useTokenDetection(chain: MaybeRef<Blockchain>, accountAddress: MaybeRef<string | null> = null) {
  const { isTaskRunning } = useTaskStore();
  const {
    getEthDetectedTokensInfo,
    fetchDetectedTokens: fetchDetectedTokensCaller,
  } = useBlockchainTokensStore();

  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const {
    optimismAddresses,
    polygonAddresses,
    arbitrumAddresses,
    baseAddresses,
    gnosisAddresses,
    scrollAddresses,
  } = storeToRefs(useChainsAccountsStore());
  const { supportsTransactions } = useSupportedChains();

  const isDetectingTaskRunning = (address: string | null) => computed(() => get(
    isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
      chain: get(chain),
      ...(address ? { address } : {}),
    }),
  ));

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
    let addresses: string[] = [];
    if (blockchain === Blockchain.OPTIMISM)
      addresses = get(optimismAddresses);
    else if (blockchain === Blockchain.ETH)
      addresses = get(ethAddresses);
    else if (blockchain === Blockchain.POLYGON_POS)
      addresses = get(polygonAddresses);
    else if (blockchain === Blockchain.ARBITRUM_ONE)
      addresses = get(arbitrumAddresses);
    else if (blockchain === Blockchain.BASE)
      addresses = get(baseAddresses);
    else if (blockchain === Blockchain.GNOSIS)
      addresses = get(gnosisAddresses);
    else if (blockchain === Blockchain.SCROLL)
      addresses = get(scrollAddresses);

    if (addresses.length > 0)
      await detectTokens(addresses);
  };

  return {
    detectingTokens,
    detectedTokens,
    getEthDetectedTokensInfo,
    detectTokens,
    detectTokensOfAllAddresses,
  };
}
