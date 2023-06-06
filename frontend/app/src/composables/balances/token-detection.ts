import { type MaybeRef } from '@vueuse/core';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { TaskType } from '@/types/task-type';
import { isTokenChain } from '@/types/blockchain/chains';

export const useTokenDetection = (
  chain: MaybeRef<Blockchain>,
  accountAddress: MaybeRef<string | null> = null
) => {
  const { isTaskRunning } = useTaskStore();
  const {
    getEthDetectedTokensInfo,
    fetchDetectedTokens: fetchDetectedTokensCaller
  } = useBlockchainTokensStore();

  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const { optimismAddresses, polygonAddresses } = storeToRefs(
    useChainsAccountsStore()
  );

  const detectingTokens = computed<boolean>(() => {
    const address = get(accountAddress);
    const blockchain = get(chain);
    return get(
      isTaskRunning(TaskType.FETCH_DETECTED_TOKENS, {
        chain: blockchain,
        ...(address ? { address } : {})
      })
    );
  });

  const detectedTokens = getEthDetectedTokensInfo(chain, accountAddress);

  const fetchDetectedTokens = async (address: string) => {
    const blockchain = get(chain);
    assert(isTokenChain(blockchain));
    await fetchDetectedTokensCaller(blockchain, address);
  };

  const detectTokens = async (addresses: string[] = []) => {
    const address = get(accountAddress);
    assert(address || addresses.length > 0);
    if (address) {
      await fetchDetectedTokens(address);
    } else {
      await Promise.allSettled(addresses.map(fetchDetectedTokens));
    }
  };

  const detectTokensOfAllAddresses = async () => {
    const blockchain = get(chain);
    let addresses: string[] = [];
    if (blockchain === Blockchain.OPTIMISM) {
      addresses = get(optimismAddresses);
    } else if (blockchain === Blockchain.ETH) {
      addresses = get(ethAddresses);
    } else if (blockchain === Blockchain.POLYGON_POS) {
      addresses = get(polygonAddresses);
    }
    if (addresses.length > 0) {
      await detectTokens(addresses);
    }
  };

  return {
    detectingTokens,
    detectedTokens,
    getEthDetectedTokensInfo,
    detectTokens,
    detectTokensOfAllAddresses
  };
};
